from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from database import Base
from typing import Optional
from datetime import datetime


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    uername: Mapped[str]
    bio: Mapped[Optional[str]]
    email: Mapped[str]
    hash_password: Mapped[str]
    pfp_link: Mapped[str]
    create_date: Mapped[datetime]
