from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


def blank_to_none(value):
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


class PatchBase(BaseModel):
    non_nullable: ClassVar[set[str]] = set()

    @model_validator(mode="before")
    @classmethod
    def drop_nulls(cls, data):
        if isinstance(data, dict):
            return {
                k: v
                for k, v in data.items()
                if not (v is None and k in cls.non_nullable)
            }
        return data


class UserBase(BaseModel):
    name: str = Field(min_length=1)
    username: str = Field(min_length=1)
    bio: str | None = Field(default=None, max_length=100)
    email: EmailStr
    pfp_link: str | None = None
    fav_genres: list[str] = Field(min_length=1)

    @field_validator("bio", "pfp_link")
    @classmethod
    def clean_blank(cls, v):
        return blank_to_none(v)


class EditBase(PatchBase):
    non_nullable = {"name", "username", "fav_genres"}

    name: str | None = Field(default=None, min_length=1)
    username: str | None = Field(default=None, min_length=1)
    bio: str | None = Field(default=None, max_length=100)
    pfp_link: str | None = None
    fav_genres: list[str] | None = Field(default=None, min_length=1)

    @field_validator("bio", "pfp_link")
    @classmethod
    def clean_blank(cls, v):
        return blank_to_none(v)


class Classified(BaseModel):
    password: str


class TasteBase(BaseModel):
    mbid: str
    rank: int = Field(gt=0)
    liked: bool = False


class EditTaste(PatchBase):
    non_nullable = {"mbid", "rank", "liked"}

    mbid: str | None = None
    rank: int | None = Field(default=None, gt=0)
    liked: bool | None = None


class ReviewBase(BaseModel):
    review_str: str = Field(max_length=400)
    rating: int = Field(lt=11, gt=0)
    mbid: str


class EditReview(PatchBase):
    non_nullable = {"review_str", "rating"}

    review_str: str | None = Field(default=None, max_length=400)
    rating: int | None = Field(default=None, gt=0, lt=11)


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
    rotation_song = "rotation_song"
    rotation_album = "rotation_album"


class UserResponse(BaseModel):
    name: str
    username: str
    bio: str | None = None
    pfp_link: str | None = None
    fav_genres: list
