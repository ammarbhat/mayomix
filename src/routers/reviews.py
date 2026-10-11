from fastapi import Depends, HTTPException, status, APIRouter
from src.models import User, Review
from src.schemas import ReviewBase, EditReview, ReviewResponse
from datetime import date
from typing import Annotated
from src.database import get_db
from sqlalchemy.exc import IntegrityError
from src.dependencies import (
    get_current_user,
)

router = APIRouter()


@router.post("/users/me/reviews")
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
    return {"message": "Review added"}


@router.get("/users/{username}/reviews")
def get_all_reviews(
    username: str, limit: int = 13, offset: int = 0, db=Depends(get_db)
):
    usr = db.query(User).filter(User.username == username).first()
    if not usr:
        raise HTTPException(status_code=404, detail="User not found")
    reviews = (
        db.query(Review)
        .filter(Review.user_id == usr.id)
        .offset(offset)
        .limit(limit)
        .all()
    )

    if not reviews:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    response = []
    for review in reviews:
        response.append(
            ReviewResponse(
                review_str=review.review_str,
                rating=review.rating,
                mbid=review.mbid,
                username=username,
                create_date=review.create_date,
                updated_date=review.updated_date,
            )
        )
    return response


@router.get("/reviews/{review_id}")
def get_review_by_id(review_id: int, db=Depends(get_db)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Not found")
    user = db.query(User).filter(User.id == review.user_id).first()
    response = ReviewResponse(
        review_str=review.review_str,
        rating=review.rating,
        mbid=review.mbid,
        username=user.username,
        create_date=review.create_date,
        updated_date=review.updated_date,
    )
    return response


@router.get("/albums/{album_mbid}/reviews")
def get_reviews_by_album(
    album_mbid: str, limit: int = 13, offset: int = 0, db=Depends(get_db)
):
    reviews = (
        db.query(Review)
        .filter(Review.mbid == album_mbid)
        .offset(offset)
        .limit(limit)
        .all()
    )
    if not reviews:
        raise HTTPException(status_code=404, detail="Not found")
    response = []
    for review in reviews:
        user = db.query(User).filter(User.id == review.user_id).first()
        response.append(
            ReviewResponse(
                review_str=review.review_str,
                rating=review.rating,
                mbid=review.mbid,
                username=user.username,
                create_date=review.create_date,
                updated_date=review.updated_date,
            )
        )
    return response


@router.patch("/users/me/reviews/{review_id}")
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
    return {"message": "Review edited"}


@router.delete("/users/me/reviews/{review_id}")
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
