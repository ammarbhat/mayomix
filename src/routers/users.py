from fastapi import Depends, HTTPException, status, APIRouter
from src.models import User, TasteEntry, Review, Connection
from src.schemas import (
    UserBase,
    Classified,
    EditBase,
    UserResponse,
)
from src.database import get_db
from datetime import date
from typing import Annotated
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, select
from src.dependencies import (
    verify_password,
    get_password_hash,
    get_current_user,
)

router = APIRouter(prefix="/users")


@router.post("")
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


@router.get("/search")
def search_users(
    username: str,
    db=Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    results = []
    searches = db.scalars(select(User).where(User.username.contains(username))).all()
    if user:
        res = UserResponse(
            username=user.username,
            pfp_link=user.pfp_link,
            name=user.name,
            fav_genres=user.fav_genres,
        )
        results.append(res)
    for u in searches:
        results.append(
            UserResponse(
                username=u.username,
                pfp_link=u.pfp_link,
                name=u.name,
                fav_genres=u.fav_genres,
            )
        )
    return results


@router.get("/me")
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


@router.get("/{username}", response_model=UserResponse)
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


@router.patch("/me")
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
    return {"message": "Edits saved"}


@router.delete("/{username}")
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
