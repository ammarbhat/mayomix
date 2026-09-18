from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String
from database import Base
from typing import List
from datetime import datetime


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    uername: Mapped[str]
    bio: Mapped[str | None]
    email: Mapped[str]
    hash_password: Mapped[str]
    pfp_link: Mapped[str | None]
    create_date: Mapped[datetime]

    taste_entries = Mapped[List["TasteEntry"]] = relationship(back_populates="user")
    reviews = Mapped[List["Review"]] = relationship(back_populates="user")


class TasteEntry(Base):
    __tablename__ = "taste_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    mbid: Mapped[str]
    category: Mapped[str]
    rank: Mapped[int]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    liked: Mapped[bool | None]

    user: Mapped["User"] = relationship(back_populates="taste_entries")


class Review(Base):
    __tablename__ = "review"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_str: Mapped[str] = mapped_column(String(400))
    rating: Mapped[int]
    user_id: Mapped[int] = mapped_column(ForeignKey="user.id")
    create_date: Mapped[datetime]
    updated_date: Mapped[datetime]

    user = Mapped["User"] = relationship(back_populates="reviews")
