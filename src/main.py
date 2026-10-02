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
)
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from src.config import settings

app = FastAPI()

origins = settings.ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
