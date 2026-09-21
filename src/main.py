from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from src.models import User, TasteEntry, Review
from src.schemas import TokenData, Token, UserBase, Classified
from datetime import timedelta, timezone, datetime, date
from typing import Annotated
from src.database import get_db, Base, engine
import requests
import httpx

app = FastAPI()
from dotenv import load_dotenv
import os

Base.metadata.create_all(bind=engine)
load_dotenv()
SECRET_KEY = os.environ["SECRET_KEY"]
password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


@app.get("/")
def root():
    return {"message": "Welcome to root!"}


def verify_password(password, hash):
    return password_hash.verify(password, hash)


def genre_tag_string(list):
    result = ""
    for l in list:
        string = f"tag:{l} OR "
        result += string
    return result[:-4]


def get_password_hash(password):
    return password_hash.hash(password)


def get_user(db, username):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    return user


def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        verify_password(password, DUMMY_HASH)
        return False
    if not verify_password(password, user.hash_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db=Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


@app.post("/token")
def login_for_acess_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db=Depends(get_db)
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@app.post("/users/")
def add_user(user: UserBase, pwd: Classified, db=Depends(get_db)):
    check = db.query(User).filter(User.username == user.username).first()
    if check:
        if check.username == user.username:
            return {"message": "username taken"}
    new_user = User(
        name=user.name,
        username=user.username,
        bio=user.bio,
        email=user.email,
        hash_password=get_password_hash(pwd.password),
        pfp_link=user.pfp_link,
        create_date=date.today(),
        fav_genres=user.fav_genres,
    )
    db.add(new_user)
    db.commit()
    return {"message": "User added!"}


@app.get("/users/{username}", response_model=UserBase)
def get_user_indb(username: str, db=Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    resp = UserBase(
        name=user.name,
        username=user.username,
        bio=user.bio,
        email=user.email,
        pfp_link=user.pfp_link,
        create_date=user.create_date,
        fav_genres=user.fav_genres,
    )
    return resp


@app.get("/search/albums")
async def search_albums_endpoint(query: str, limit: int = 25, db=Depends(get_db)):
    test = db.query(User).filter(User.username == "ammar").first()
    genre_string = genre_tag_string(test.fav_genres)
    mod_query = f'releasegroup:"{query}" AND ({genre_string}) AND primarytype:album'
    url = "https://musicbrainz.org/ws/2/release-group/"
    params = {"query": mod_query, "fmt": "json", "limit": limit}
    headers = {"User-Agent": "mayo-mix/0.1 (https://github.com/ammarbhat)"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        return response.json()


@app.post("/taste/")
def add_taste_entry(
    current: Annotated[User, Depends(get_current_user)], db=Depends(get_db)
):
    return current
