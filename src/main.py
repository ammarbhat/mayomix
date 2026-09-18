from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from models import User, TasteEntry, Review

app = FastAPI()
from dotenv import load_dotenv
import os

load_dotenv()
SECRET_KEY = os.environ["SECRET_KEY"]
password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/")
def root():
    return {"message": "Welcome to root!"}


def verify_password(password, hash):
    return password_hash.verify(password, hash)


def get_password_hash(password):
    return password_hash.hash(password)


def get_user(db, username):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    return user
