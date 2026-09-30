from fastapi import Depends, HTTPException, status, APIRouter
from src.models import User, Review, Connection
from typing import Annotated
from src.database import get_db
from src.dependencies import (
    get_current_user,
)

router = APIRouter()


@router.get("/activity")
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
