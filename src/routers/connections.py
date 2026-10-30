from fastapi import Depends, HTTPException, status, APIRouter
from src.models import User, Connection
from src.schemas import ConnectionResponse
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


@router.get("/me", response_model=list[ConnectionResponse])
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
    response = []
    if len(respli) != 0:
        for con in respli:
            if con.user_id1 == current.id:
                user = db.query(User).filter(User.id == con.user_id2).first()
                response.append(
                    ConnectionResponse(
                        con_id=con.id,
                        user_id=con.user_id2,
                        name=user.name,
                        username=user.username,
                        pfp_link=user.pfp_link,
                    )
                )
            else:
                user = db.query(User).filter(User.id == con.user_id1).first()
                response.append(
                    ConnectionResponse(
                        con_id=con.id,
                        user_id=con.user_id1,
                        name=user.name,
                        username=user.username,
                        pfp_link=user.pfp_link,
                    )
                )
    return response


@router.get("/me/pending", response_model=list[ConnectionResponse])
def get_pending_connections(
    current: Annotated[User, Depends(get_current_user)], db=Depends(get_db)
):
    connect = (
        db.query(Connection)
        .filter(Connection.user_id2 == current.id, Connection.accepted == False)
        .all()
    )
    response = []
    if len(connect) != 0:
        for con in connect:
            user = db.query(User).filter(User.id == con.user_id1).first()
            response.append(
                ConnectionResponse(
                    con_id=con.id,
                    user_id=con.user_id1,
                    name=user.name,
                    username=user.username,
                    pfp_link=user.pfp_link,
                )
            )
    return response


@router.get("/me/sent", response_model=list[ConnectionResponse])
def get_sent_connections(
    current: Annotated[User, Depends(get_current_user)], db=Depends(get_db)
):
    connect = (
        db.query(Connection)
        .filter(Connection.user_id1 == current.id, Connection.accepted == False)
        .all()
    )
    response = []
    for con in connect:
        user = db.query(User).filter(User.id == con.user_id2).first()
        response.append(
            ConnectionResponse(
                con_id=con.id,
                user_id=con.user_id2,
                name=user.name,
                username=user.username,
                pfp_link=user.pfp_link,
            )
        )
    return response


@router.get("/me/status/{username}")
def check_connection_status(
    username: str,
    current: Annotated[User, Depends(get_current_user)],
    db=Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    con1 = db.scalars(
        select(Connection).where(
            Connection.user_id1 == current.id, Connection.user_id2 == user.id
        )
    ).first()
    con2 = db.scalars(
        select(Connection).where(
            Connection.user_id1 == user.id, Connection.user_id2 == current.id
        )
    ).first()
    if not con1 and not con2:
        return {"status": "not_found"}
    elif con1:
        if con1.accepted == True:
            return {"status": "connected"}
        elif con1.accepted == False:
            return {"status": "pending_sent"}
    elif con2:
        if con2.accepted == True:
            return {"status": "connected"}
        elif con2.accepted == False:
            return {"status": "pending_received"}
