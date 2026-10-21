from fastapi import Depends, HTTPException, status, APIRouter
from src.models import User, Review, Connection
from typing import Annotated
from src.database import get_db
from src.schemas import ReviewResponse
from pydantic import Field
from src.dependencies import (
    get_current_user,
)

router = APIRouter()


@router.get("/activity", response_model=list[ReviewResponse])
def get_activity(
    current: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Field(default=13, gt=12, lt=30)],
    offset: Annotated[int, Field(default=0, ge=0)],
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

    ids = {current.id}
    for c in connections:
        ids.add(c.user_id1)
        ids.add(c.user_id2)

    activity = (
        db.query(Review)
        .filter(Review.user_id.in_(ids))
        .order_by(Review.create_date.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    response = []
    for review in activity:
        user = db.query(User).filter(User.id == review.user_id).first()
        response.append(
            ReviewResponse(
                id=review.id,
                review_str=review.review_str,
                mbid=review.mbid,
                rating=review.rating,
                create_date=review.create_date,
                updated_date=review.updated_date,
                username=user.username,
            )
        )
    return response
