from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.routers import (
    users,
    music,
    taste,
    reviews,
    connections,
    auth,
    activity,
    health,
    docs,
)
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from src.config import settings
from src.logger import logger
import time

app = FastAPI()
logger.info("Starting API...")
origins = settings.ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_headers_and_logging(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    log_dict = {
        "url": request.url.path,
        "method": request.method,
        "process_time": process_time,
    }
    logger.info(log_dict, extra=log_dict)
    return response


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409, content={"detail": "This conflicts with existing data."}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500, content={"detail": "Something went wrong. Please try again."}
    )


@app.get("/")
def root():
    return {"message": "Welcome to root!"}


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(music.router)
app.include_router(taste.router)
app.include_router(reviews.router)
app.include_router(connections.router)
app.include_router(activity.router)
app.include_router(docs.router)
