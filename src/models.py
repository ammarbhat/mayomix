from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    ForeignKey,
    String,
    JSON,
    UniqueConstraint,
    CheckConstraint,
    Boolean,
)
from src.database import Base
from typing import List
from datetime import date


class User(Base):
    __tablename__ = "user"
    __table_args__ = (
        UniqueConstraint("username", name="uq_username"),
        UniqueConstraint("email", name="uq_email"),
    )

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
        UniqueConstraint("rank", "category", "user_id", name="uq_rank_catgory_user_id"),
        UniqueConstraint(
            "mbid", "category", "user_id", name="uq_mbid_category_user_id"
        ),
        CheckConstraint("rank > 0 AND rank < 11", name="non_zero_rank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mbid: Mapped[str]
    category: Mapped[str]
    rank: Mapped[int]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    liked: Mapped[bool]

    user: Mapped["User"] = relationship(back_populates="taste_entries")


class Review(Base):
    __tablename__ = "review"
    __table_args__ = (
        CheckConstraint("rating <= 10", name="rating_limit"),
        UniqueConstraint("user_id", "mbid", name="uq_user_id_mbid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    review_str: Mapped[str] = mapped_column(String(400))
    mbid: Mapped[str] = mapped_column(index=True)
    rating: Mapped[int]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    create_date: Mapped[date]
    updated_date: Mapped[date | None]

    user: Mapped["User"] = relationship(back_populates="reviews")


class Connection(Base):
    __tablename__ = "connection"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id1: Mapped[int] = mapped_column(index=True)
    user_id2: Mapped[int] = mapped_column(index=True)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    connect_date: Mapped[date | None]
