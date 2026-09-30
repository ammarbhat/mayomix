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
from src.routers import users, music, taste, reviews

app = FastAPI()

Base.metadata.create_all(bind=engine)

ACCESS_TOKEN_EXPIRE_MINUTES = 30

app.include_router(users.router)
app.include_router(music.router)
app.include_router(taste.router)
app.include_router(reviews.router)


@app.get("/")
def root():
    return {"message": "Welcome to root!"}


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


@app.post("/connections/{user_id}")
def send_connection(
    user_id: int,
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):
    usr = db.query(User).filter(User.id == user_id).first()
    if not usr:
        raise HTTPException(status_code=404, detail="Not found")
    if user_id == current.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send connection to self",
        )
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
            status_code=status.HTTP_409_CONFLICT, detail="Connection already exists"
        )
    new_con = Connection(user_id1=current.id, user_id2=user_id)
    db.add(new_con)
    db.commit()
    return {"message": "Connection request sent"}


@app.patch("/connections/{con_id}/accept")
def accept_connection(
    con_id: int, current: Annotated[User, Depends(get_current_user)], db=Depends(get_db)
):

    connect = (
        db.query(Connection)
        .filter(Connection.id == con_id, Connection.user_id2 == current.id)
        .first()
    )
    if not connect:
        raise HTTPException(status_code=404, detail="Not found")
    if connect.accepted == True:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    connect.accepted = True
    connect.connect_date = date.today()
    db.commit()
    return {"message": "Connection accepted"}


@app.delete("/connections/{con_id}")
def delete_request_connection(
    current: Annotated[User, Depends(get_current_user)], con_id: int, db=Depends(get_db)
):
    connect = db.scalars(
        select(Connection).where(
            or_(Connection.user_id2 == current.id, Connection.user_id1 == current.id),
            (Connection.id == con_id),
        ),
    ).first()

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
    if not respli:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
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
