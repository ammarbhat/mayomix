from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from src.models import User
from src.schemas import TokenData
from src.database import get_db
from datetime import timedelta, timezone, datetime, date
from typing import Annotated
from src.config import settings

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def check_taste_entry(entry, category):
    if category == "top_songs":
        if entry.rank > 10:
            return False
        else:
            return True
    elif category == "rotation_song":
        if entry.rank > 6:
            return False
    elif entry.rank > 3:
        return False
    else:
        return True


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
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db=Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
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
