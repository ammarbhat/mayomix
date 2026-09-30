from fastapi import Depends, HTTPException, status, APIRouter
from src.models import User, Connection

from datetime import date
from typing import Annotated
from src.database import get_db
from sqlalchemy import or_, select
from src.dependencies import (
    get_current_user,
)

router = APIRouter(prefix="/connections")


@router.post("/{user_id}")
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


@router.patch("/{con_id}/accept")
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


@router.delete("/{con_id}")
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


@router.get("/me")
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


@router.get("/me/pending")
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


@router.get("/me/sent")
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
