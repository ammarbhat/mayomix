from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from src.models import User, TasteEntry, Review, Connection
from src.schemas import (
    Token,
    UserBase,
    Classified,
    TasteBase,
    EditBase,
    CategorySelect,
    EditTaste,
    ReviewBase,
    EditReview,
    UserResponse,
)
from datetime import timedelta, date
from typing import Annotated
from src.database import get_db, Base, engine
from sqlalchemy.exc import IntegrityError
import httpx
from sqlalchemy import or_, select
from src.dependencies import (
    check_taste_entry,
    verify_password,
    genre_tag_string,
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from src.routers import users, music, taste, reviews, connections, auth

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(music.router)
app.include_router(taste.router)
app.include_router(reviews.router)
app.include_router(connections.router)


@app.get("/")
def root():
    return {"message": "Welcome to root!"}


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
    if not connections:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    ids = {current.id}
    for c in connections:
        ids.add(c.user_id1)
        ids.add(c.user_id2)

    activity = (
        db.query(Review)
        .filter(Review.user_id.in_(ids))
        .order_by(Review.create_date.desc())
        .limit(7)
        .all()
    )
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return activity
