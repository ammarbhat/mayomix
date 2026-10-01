from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import users, music, taste, reviews, connections, auth, activity
from dotenv import load_dotenv
import os

app = FastAPI()
load_dotenv()

origins = os.environ["origins"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Welcome to root!"}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(music.router)
app.include_router(taste.router)
app.include_router(reviews.router)
app.include_router(connections.router)
app.include_router(activity.router)
