from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Literal
from enum import Enum


class UserBase(BaseModel):
    name: str
    username: str
    bio: str | None = None
    email: EmailStr
    pfp_link: str | None = None
    create_date: date
    fav_genres: list


class EditBase(BaseModel):
    name: str
    username: str
    bio: str
    pfp_link: str
    fav_genres: list


class Classified(BaseModel):
    password: str


class TasteBase(BaseModel):
    mbid: str
    rank: int
    liked: bool
    category: Literal["top_songs", "top_albums", "top_artists", "top_genres"]


class ReviewBase(BaseModel):
    review_str: str
    rating: int
    user_id: int
    create_date: date
    updated_date: date


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class CategorySelect(str, Enum):
    top_songs = "top_songs"
    top_albums = "top_albums"
    top_artists = "top_artists"
    top_genres = "top_genres"
