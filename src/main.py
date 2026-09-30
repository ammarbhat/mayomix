from fastapi import FastAPI
from src.database import Base, engine

from src.routers import users, music, taste, reviews, connections, auth, activity

app = FastAPI()

Base.metadata.create_all(bind=engine)


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
