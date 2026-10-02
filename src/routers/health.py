from fastapi import APIRouter, Depends
from src.database import get_db
from sqlalchemy import text
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/health")


@router.get("")
def check_health(db=Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        return JSONResponse(
            status_code=503, content={"status": "ok", "database": "error"}
        )
