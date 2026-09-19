from pydantic import BaseModel, EmailStr
from datetime import date


class UserBase(BaseModel):
    name: str
    username: str
    bio: str | None = None
    email: EmailStr
    pfp_link: str | None = None
    create_date: date


class Classified(BaseModel):
    password: str


class TasteBase(BaseModel):
    mbid: str
    rank: int
    user_id: int
    liked: bool


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
