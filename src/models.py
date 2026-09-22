from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, JSON, UniqueConstraint, CheckConstraint
from src.database import Base
from typing import List
from datetime import datetime, date


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    username: Mapped[str]
    bio: Mapped[str | None]
    email: Mapped[str]
    hash_password: Mapped[str]
    pfp_link: Mapped[str | None]
    create_date: Mapped[date]
    fav_genres: Mapped[list] = mapped_column(JSON)

    taste_entries: Mapped[List["TasteEntry"]] = relationship(back_populates="user")
    reviews: Mapped[List["Review"]] = relationship(back_populates="user")


class TasteEntry(Base):
    __tablename__ = "taste_entry"
    __table_args__ = (
        UniqueConstraint("rank", "mbid", name="uq_rank_mbid"),
        CheckConstraint("rank > 0", name="non_zero_rank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mbid: Mapped[str]
    category: Mapped[str]
    rank: Mapped[int]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    liked: Mapped[bool | None]

    user: Mapped["User"] = relationship(back_populates="taste_entries")


class Review(Base):
    __tablename__ = "review"
    __table_args__ = (
        UniqueConstraint("mbid", name="uq_mbid"),
        CheckConstraint("rating <= 10", name="rating_limit"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    review_str: Mapped[str] = mapped_column(String(400))
    mbid: Mapped[str]
    rating: Mapped[int]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    create_date: Mapped[date]
    updated_date: Mapped[date | None]

    user: Mapped["User"] = relationship(back_populates="reviews")
