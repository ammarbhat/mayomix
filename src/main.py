from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
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
from sqlalchemy import or_, select, and_
from dotenv import load_dotenv
import os
from src.dependencies import (
    check_taste_entry,
    verify_password,
    genre_tag_string,
    get_password_hash,
    get_user,
    authenticate_user,
    create_access_token,
    get_current_user,
)

app = FastAPI()

Base.metadata.create_all(bind=engine)
load_dotenv()
SECRET_KEY = os.environ["SECRET_KEY"]
password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


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


@app.post("/users")
def add_user(user: UserBase, pwd: Classified, db=Depends(get_db)):
    check = db.scalars(
        select(User).where(
            or_(User.username == user.username, User.email == user.email)
        )
    ).first()
    if check:
        if check.username == user.username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="username already exists",
            )
        if check.email == user.email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="email already exists",
            )
    new_user = User(
        name=user.name,
        username=user.username,
        bio=user.bio,
        email=user.email,
        hash_password=get_password_hash(pwd.password),
        pfp_link=user.pfp_link,
        create_date=date.today(),
        fav_genres=user.fav_genres,
    )
    db.add(new_user)
    db.commit()
    return {"message": "User added!"}


@app.get("/users/me")
def get_me(current: Annotated[User, Depends(get_current_user)]):
    user = UserBase(
        name=current.name,
        username=current.username,
        bio=current.bio,
        email=current.email,
        pfp_link=current.pfp_link,
        create_date=current.create_date,
        fav_genres=current.fav_genres,
    )
    return user


@app.get("/users/{username}", response_model=UserResponse)
def get_user_by_username(username: str, db=Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )
    resp = UserResponse(
        name=user.name,
        username=user.username,
        bio=user.bio,
        pfp_link=user.pfp_link,
        fav_genres=user.fav_genres,
    )
    return resp


@app.patch("/users/me")
def edit_user(
    edits: EditBase,
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):

    user = db.query(User).filter(User.username == current.username).first()
    test_user = (
        db.query(User)
        .filter(User.id != current.id, User.username == edits.username)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if test_user:
        raise HTTPException(status_code=409, detail="username already taken")

    updates = edits.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    return {"message": "Edits saved"}


@app.delete("/users/{username}")
def delete_user(
    username: str,
    current: Annotated[User, Depends(get_current_user)],
    pwd: Classified,
    db=Depends(get_db),
):
    if username != current.username:
        raise HTTPException(status_code=404, detail="Not found")
    if not verify_password(pwd.password, current.hash_password):
        raise HTTPException(status_code=401, detail="Incorrect password")
    user = db.query(User).filter(User.username == current.username).first()
    reviews = db.query(Review).filter(Review.user_id == current.id).all()
    tastes = db.query(TasteEntry).filter(TasteEntry.user_id == current.id).all()
    connections = db.scalars(
        select(Connection).where(
            or_(Connection.user_id1 == current.id, Connection.user_id2 == current.id)
        )
    ).all()
    if reviews:
        for r in reviews:
            db.delete(r)
    if tastes:
        for t in tastes:
            db.delete(t)
    if connections:
        for c in connections:
            db.delete(c)
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


@app.get("/search/albums")
async def search_albums_endpoint(
    query: str,
    current: Annotated[User, Depends(get_current_user)],
    limit: int = 25,
    db=Depends(get_db),
):
    user = db.query(User).filter(User.username == current.username).first()
    genre_string = genre_tag_string(user.fav_genres)
    mod_query = f'releasegroup:"{query}" AND ({genre_string}) AND primarytype:album'
    url = "https://musicbrainz.org/ws/2/release-group/"
    params = {"query": mod_query, "fmt": "json", "limit": limit}
    headers = {"User-Agent": "mayo-mix/0.1 (https://github.com/ammarbhat)"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        return response.json()


@app.get("/search/artists")
async def search_artits(query: str, limit: int = 6):
    url = "https://musicbrainz.org/ws/2/artist/"
    params = {"query": query, "fmt": "json", "limit": limit}
    headers = {"User-Agent": "mayo-mix/0.1 (https://github.com/ammarbhat)"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        return response.json()


@app.get("/search/songs")
async def search_songs(query: str, limit: int = 10):
    mod_query = f'recording:"{query}"'
    url = "https://musicbrainz.org/ws/2/recording/"
    params = {"query": mod_query, "fmt": "json", "limit": limit}
    headers = {"User-Agent": "mayo-mix/0.1 (https://github.com/ammarbhat)"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        return response.json()


@app.get("/albums/{mbid}")
async def get_album(mbid: str):
    url = (
        f"https://musicbrainz.org/ws/2/release-group/"
        f"{mbid}?inc=genres+releases&fmt=json"
    )

    headers = {"User-Agent": "mayo-mix/0.1 (https://github.com/ammarbhat)"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch album from MusicBrainz",
            )

        album_meta = response.json()

        # Use the release-group MBID directly
        cover_url = f"https://coverartarchive.org/" f"release-group/{mbid}/front"

        cover_response = await client.head(cover_url)

        if cover_response.status_code == 404:
            cover_url = None

    return {"meta": album_meta, "cover_url": cover_url}


@app.post("/users/me/taste")
def add_taste_entry(
    entry: TasteBase,
    category: CategorySelect,
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):
    test = db.scalars(
        select(TasteEntry).where(
            TasteEntry.user_id == current.id,
            TasteEntry.category == category,
            or_(
                TasteEntry.mbid == entry.mbid,
                TasteEntry.rank == entry.rank,
            ),
        )
    ).first()
    if test:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="already taken"
        )
    if not check_taste_entry(entry, category):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="rank limit reached"
        )
    taste = TasteEntry(
        mbid=entry.mbid,
        category=category,
        rank=entry.rank,
        user_id=current.id,
        liked=entry.liked,
    )
    try:
        db.add(taste)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    return {"message": "Entry added"}


@app.delete("/users/me/taste/{id}")
def delete_taste_entry(
    id: int, current: Annotated[User, Depends(get_current_user)], db=Depends(get_db)
):
    taste_entry = (
        db.query(TasteEntry)
        .filter(TasteEntry.id == id, TasteEntry.user_id == current.id)
        .first()
    )
    if not taste_entry:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(taste_entry)
    db.commit()
    return {"message": "Note deleted"}


@app.get("/users/{username}/taste")
def get_user_entries(username: str, category: CategorySelect, db=Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    taste_entries = (
        db.query(TasteEntry)
        .filter(TasteEntry.category == category, TasteEntry.user_id == user.id)
        .all()
    )
    if not taste_entries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No entries found"
        )
    return taste_entries


@app.patch("/users/me/taste/{entry_id}")
def edit_entry(
    entry_id: int,
    edits: EditTaste,
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):
    entry = (
        db.query(TasteEntry)
        .filter(TasteEntry.user_id == current.id, TasteEntry.id == entry_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    updates = edits.model_dump(exclude_unset=True)
    conditions = []
    if updates.get("mbid") is not None:
        conditions.append(TasteEntry.mbid == updates["mbid"])
    if updates.get("rank") is not None:
        conditions.append(TasteEntry.rank == updates["rank"])

    if conditions:
        conflict = db.scalars(
            select(TasteEntry).where(
                TasteEntry.user_id == current.id,
                TasteEntry.category == entry.category,
                TasteEntry.id != entry.id,
                or_(*conditions),
            )
        ).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="already taken"
            )

    if updates.get("rank") is not None:
        if not check_taste_entry(edits, entry.category):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="rank limit reached"
            )
    for field, value in updates.items():
        setattr(entry, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    return {"message": "Note edited"}


@app.post("/users/me/reviews")
def add_review(
    review: ReviewBase,
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):
    test = (
        db.query(Review)
        .filter(Review.mbid == review.mbid, Review.user_id == current.id)
        .first()
    )
    if test:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Review already exists"
        )
    new_review = Review(
        review_str=review.review_str,
        rating=review.rating,
        user_id=current.id,
        mbid=review.mbid,
        create_date=date.today(),
    )
    try:
        db.add(new_review)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Review already exists"
        )
    return {"message": "Review added"}


@app.get("/users/{username}/reviews")
def get_all_reviews(username: str, db=Depends(get_db)):
    usr = db.query(User).filter(User.username == username).first()
    if not usr:
        raise HTTPException(status_code=404, detail="User not found")
    reviews = db.query(Review).filter(Review.user_id == usr.id).all()

    if not reviews:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return reviews


@app.get("/reviews/{review_id}")
def get_review_by_id(review_id: int, db=Depends(get_db)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Not found")
    return review


@app.get("/albums/{album_mbid}/reviews")
def get_reviews_by_album(album_mbid: str, db=Depends(get_db)):
    reviews = db.query(Review).filter(Review.mbid == album_mbid).all()
    if not reviews:
        raise HTTPException(status_code=404, detail="Not found")
    return reviews


@app.patch("/users/me/reviews/{review_id}")
def edit_review(
    review_id: int,
    edit: EditReview,
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Not found")
    if current.id != review.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    updates = edit.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(review, field, value)
    review.updated_date = date.today()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    return {"message": "Review edited"}


@app.delete("/users/me/reviews/{review_id}")
def delete_review(
    review_id: int,
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Not found")
    if current.id != review.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    db.delete(review)
    db.commit()
    return {"message": "Review deleted"}


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
