from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from src.models import User, TasteEntry, Review, Connection
from src.schemas import (
    TokenData,
    Token,
    UserBase,
    Classified,
    TasteBase,
    EditBase,
    CategorySelect,
    EditTaste,
    ReviewBase,
    EditReview,
)
from datetime import timedelta, timezone, datetime, date
from typing import Annotated
from src.database import get_db, Base, engine
from sqlalchemy.exc import IntegrityError
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


def select_best_release(release_group: dict) -> str | None:
    releases = release_group.get("releases", [])

    if not releases:
        return None

    group_title = release_group.get("title", "")

    official = [r for r in releases if r.get("status") == "Official"]

    candidates = official if official else releases

    exact_title_matches = [r for r in candidates if r.get("title") == group_title]

    if exact_title_matches:
        candidates = exact_title_matches

    candidates = sorted(candidates, key=lambda r: r.get("date") or "9999-99-99")

    return candidates[0].get("id")


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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="username already exists",
            )
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


@app.get("/users/me")
def get_me(current: Annotated[User, Depends(get_current_user)]):
    user = UserBase(
        name=current.name,
        username=current.username,
        bio=current.bio,
        email=current.email,
        pfp_link=current.pfp_link,
        create_date=current.create_date,
        fav_genres=current.fav_genres,
    )
    return user


@app.get("/users/{username}", response_model=UserBase)
def get_user_by_username(username: str, db=Depends(get_db)):
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


@app.patch("/users/{id}")
def edit_user(edits: EditBase, id: int, db=Depends(get_db)):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.name = edits.name
    user.username = edits.username
    user.bio = edits.bio
    user.pfp_link = edits.pfp_link
    user.fav_genres = edits.fav_genres
    db.commit()
    return {"message": "Edits saved"}


@app.delete("/users/{id}")
def delete_user(
    id: int,
    current: Annotated[User, Depends(get_current_user)],
    pwd: Classified,
    db=Depends(get_db),
):
    if id != current.id:
        raise HTTPException(status_code=404, detail="Not found")
    if not verify_password(pwd.password, current.hash_password):
        raise HTTPException(status_code=401, detail="Incorrect password")
    db.delete(current)
    db.commit()
    return {"message": "User deleted"}


@app.get("/search/albums")
async def search_albums_endpoint(
    query: str,
    current: Annotated[User, Depends(get_current_user)],
    limit: int = 25,
    db=Depends(get_db),
):
    user = db.query(User).filter(User.username == current.username).first()
    genre_string = genre_tag_string(user.fav_genres)
    mod_query = f'releasegroup:"{query}" AND ({genre_string}) AND primarytype:album'
    url = "https://musicbrainz.org/ws/2/release-group/"
    params = {"query": mod_query, "fmt": "json", "limit": limit}
    headers = {"User-Agent": "mayo-mix/0.1 (https://github.com/ammarbhat)"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        return response.json()


@app.get("/search/artists")
async def search_artits(query: str, limit: int = 6):
    url = "https://musicbrainz.org/ws/2/artist/"
    params = {"query": query, "fmt": "json", "limit": limit}
    headers = {"User-Agent": "mayo-mix/0.1 (https://github.com/ammarbhat)"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        return response.json()


@app.get("/search/songs")
async def search_songs(query: str, limit: int = 10):
    mod_query = f'recording:"{query}"'
    url = "https://musicbrainz.org/ws/2/recording/"
    params = {"query": mod_query, "fmt": "json", "limit": limit}
    headers = {"User-Agent": "mayo-mix/0.1 (https://github.com/ammarbhat)"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        return response.json()


@app.get("/albums/{mbid}")
async def get_album(mbid: str):
    url = (
        f"https://musicbrainz.org/ws/2/release-group/"
        f"{mbid}?inc=genres+releases&fmt=json"
    )

    headers = {"User-Agent": "mayo-mix/0.1 (https://github.com/ammarbhat)"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch album from MusicBrainz",
            )

        album_meta = response.json()

        # Use the release-group MBID directly
        cover_url = f"https://coverartarchive.org/" f"release-group/{mbid}/front"

        cover_response = await client.head(cover_url)

        if cover_response.status_code == 404:
            cover_url = None

    return {"meta": album_meta, "cover_url": cover_url}


@app.post("/users/me/taste/")
def add_taste_entry(
    entry: TasteBase,
    category: CategorySelect,
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):
    taste = TasteEntry(
        mbid=entry.mbid,
        category=category,
        rank=entry.rank,
        user_id=current.id,
        liked=entry.liked,
    )
    try:
        db.add(taste)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Rank already taken"
        )
    return {"message": "Entry added"}


@app.delete("/users/me/taste/{id}")
def del_taste_entry(
    id: int, current: Annotated[User, Depends(get_current_user)], db=Depends(get_db)
):
    taste_entry = db.query(TasteEntry).filter(TasteEntry.id == id).first()
    user = db.query(User).filter(User.username == current.username).first()
    if not taste_entry:
        raise HTTPException(status_code=404, detail="Not found")
    if not user:
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(taste_entry)
    db.commit()
    return {"message": "Note deleted"}


@app.get("/users/{user_id}/taste")
def get_user_entry(user_id: int, category: CategorySelect, db=Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    taste_entries = (
        db.query(TasteEntry)
        .filter(TasteEntry.category == category, TasteEntry.user_id == user_id)
        .all()
    )
    if not taste_entries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No entries found"
        )
    return taste_entries


@app.patch("/users/me/taste/{entry_id}")
def edit_entry(
    edits: EditTaste,
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):
    entry = db.query(TasteEntry).filter(TasteEntry.user_id == current.id).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    entry.mbid = edits.mbid
    entry.rank = edits.rank
    entry.liked = edits.liked
    db.commit()
    return {"message": "Note edited"}


@app.post("/users/me/reviews")
def add_review(
    review: ReviewBase,
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):
    test = (
        db.query(Review)
        .filter(Review.mbid == review.mbid, Review.user_id == current.id)
        .first()
    )
    if test:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Review already exists"
        )
    new_review = Review(
        review_str=review.review_str,
        rating=review.rating,
        user_id=current.id,
        mbid=review.mbid,
        create_date=date.today(),
    )
    try:
        db.add(new_review)
        db.commit()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Review already exists"
        )
    return {"message": "Review added"}


@app.get("/users/{user_id}/reviews")
def get_all_reviews(user_id: int, db=Depends(get_db)):
    reviews = db.query(Review).filter(Review.user_id == user_id).all()
    if not reviews:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return reviews


@app.get("/reviews/{review_id}")
def get_review_by_id(reveiw_id: int, db=Depends(get_db)):
    review = db.query(Review).filter(Review.id == reveiw_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Not found")
    return review


@app.get("/albums/{album_mbid}/reviews")
def get_reviews_by_album(album_mbid: str, db=Depends(get_db)):
    reviews = db.query(Review).filter(Review.mbid == album_mbid).all()
    if not reviews:
        raise HTTPException(status_code=404, detail="Not found")
    return reviews


@app.patch("/users/me/reviews/{review_id}")
def edit_review(
    review_id: int,
    edit: EditReview,
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Not found")
    if current.id != review.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    review.review_str = edit.review_str
    review.rating = edit.rating
    review.updated_date = date.today()
    db.commit()
    return {"message": "Review edited"}


@app.delete("users/me/reviews/{review_id}")
def delete_review(
    review_id: int,
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Not found")
    if current.id != review.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    db.delete(review)
    db.commit()
    return {"message": "Review deleted"}


@app.post("/connections/{user_id}")
def send_connection(
    user_id: int,
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):
    con1 = (
        db.query(Connection)
        .filter(Connection.user_id1 == current.id, Connection.user_id2 == user_id)
        .first()
    )
    con2 = (
        db.query(Connection)
        .filter(Connection.user_id1 == user_id, Connection.user_id2 == current.id)
        .first()
    )
    if con1 or con2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Connection already exists"
        )
    new_con = Connection(user_id1=current.id, user_id2=user_id)
    reciever = db.query(User).filter(User.id == user_id).first()
    if not reciever:
        raise HTTPException(status_code=404, detail="Not found")
    db.add(new_con)
    db.commit()
    return {"message": "Connection request sent"}


@app.patch("/connections/{con_id}/accept")
def accept_connection(
    con_id: int, current: Annotated[User, Depends(get_current_user)], db=Depends(get_db)
):

    connect = db.query(Connection).filter(Connection.id == con_id).first()
    if current.id != connect.user_id1:
        raise HTTPException(status_code=400, detail="Unauthorized")
    if not connect:
        raise HTTPException(status_code=404, detail="Not found")
    connect.accepted = True
    connect.connect_date = date.today()
    db.commit()
    return {"message": "Connection accepted"}


@app.delete("/connections/{con_id}/delete")
def delete_req_friend(con_id: int, db=Depends(get_db)):
    connect = db.query(Connection).filter(Connection.id == con_id).first()
    if not connect:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(connect)
    db.commit()
    return {"message": "Connection deleted"}


@app.get("/connections/me")
def get_connections(
    current: Annotated[User, Depends(get_current_user)], db=Depends(get_db)
):
    connect1 = (
        db.query(Connection)
        .filter(Connection.user_id1 == current.id, Connection.accepted == True)
        .all()
    )
    connect2 = (
        db.query(Connection)
        .filter(Connection.user_id2 == current.id, Connection.accepted == True)
        .all()
    )
    respli = connect1 + connect2
    return respli


@app.get("/connections/me/pending")
def get_pending_connections(
    current: Annotated[User, Depends(get_current_user)], db=Depends(get_db)
):
    connect = (
        db.query(Connection)
        .filter(Connection.user_id2 == current.id, Connection.accepted == False)
        .all()
    )
    if not connect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return connect


@app.get("/connections/me/sent")
def get_sent_connections(
    current: Annotated[User, Depends(get_current_user)], db=Depends(get_db)
):
    connect = (
        db.query(Connection)
        .filter(Connection.user_id1 == current.id, Connection.accepted == False)
        .all()
    )
    if not connect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return connect


@app.get("/activity")
def get_activity(
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):
    connections = (
        db.query(Connection)
        .filter(
            ((Connection.user_id1 == current.id) | (Connection.user_id2 == current.id)),
            Connection.accepted == True,
        )
        .all()
    )

    ids = {current.id}
    for c in connections:
        ids.add(c.user_id1)
        ids.add(c.user_id2)

    activity = (
        db.query(Review)
        .filter(Review.user_id.in_(ids))
        .order_by(Review.date_created.desc())
        .limit(7)
        .all()
    )
    return activity
