from fastapi import Depends, HTTPException, status, APIRouter
from src.models import User, TasteEntry
from src.schemas import (
    TasteBase,
    CategorySelect,
    EditTaste,
)
from typing import Annotated
from src.database import get_db
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, select
from src.dependencies import (
    check_taste_entry,
    get_current_user,
)

router = APIRouter(prefix="/users")


@router.post("/me/taste")
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
    return {"message": "Entry added"}


@router.delete("/me/taste/{id}")
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


@router.get("/{username}/taste")
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


@router.patch("/me/taste/{entry_id}")
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
    return {"message": "Note edited"}
