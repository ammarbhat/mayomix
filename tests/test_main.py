from fastapi.testclient import TestClient
import pytest
from src.main import app, get_current_user
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, get_db
from src.models import TasteEntry, User, Review, Connection
from datetime import date
from sqlalchemy.pool import StaticPool
from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordRequestForm

password_hash = PasswordHash.recommended()

client = TestClient(app)
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=engine)
TestingSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    return User(
        id=1,
        name="amm",
        username="testusr",
        email="test@test.com",
        hash_password=password_hash.hash("string"),
        create_date=date.today(),
        fav_genres=["pop", "rock"],
    )


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture
def test_db():
    db = TestingSession()
    yield db
    db.close()


@pytest.fixture(autouse=True)
def seed_test_user(setup_and_teardown_db):
    db = TestingSession()
    user = User(
        id=1,
        name="amm",
        username="testusr",
        email="test@test.com",
        hash_password=password_hash.hash("string"),
        create_date=date.today(),
        fav_genres=["pop", "rock"],
    )
    db.add(user)
    db.commit()
    db.close()


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_root():
    response = client.get("/")
    assert response.status_code == 200


def test_token():
    response = client.post(
        "/token", data={"username": "testusr", "password": "string", "scope": ""}
    )
    assert response.status_code == 200


def test_token_unauthorized():
    response = client.post(
        "/token", data={"username": "testusssr", "password": "string", "scope": ""}
    )
    assert response.status_code == 401


def test_add_users(test_db):
    response = client.post(
        "/users/",
        json={
            "user": {
                "name": "string",
                "username": "string",
                "bio": "string",
                "email": "user@example.com",
                "pfp_link": "string",
                "create_date": "2026-09-24",
                "fav_genres": ["string"],
            },
            "pwd": {"password": "string"},
        },
    )
    assert response.status_code == 200


def test_add_user_duplicate_username(test_db):

    response = client.post(
        "/users/",
        json={
            "user": {
                "name": "string",
                "username": "testusr",
                "bio": "string",
                "email": "user@example.com",
                "pfp_link": "string",
                "create_date": "2026-09-24",
                "fav_genres": ["string"],
            },
            "pwd": {"password": "string"},
        },
    )
    assert response.status_code == 400


def test_add_user_incomplete_data(test_db):
    response = client.post(
        "/users/",
        json={
            "user": {
                "name": "string",
                "username": "string",
                "bio": "string",
                "pfp_link": "string",
                "create_date": "2026-09-24",
                "fav_genres": ["string"],
            },
            "pwd": {"password": "string"},
        },
    )
    assert response.status_code == 422


def test_get_me():
    response = client.get("/users/me")
    assert response.status_code == 200


def test_get_user_by_username():
    response = client.get(f"/users/{"testusr"}")
    assert response.status_code == 200


def test_get_user_by_username_not_found():
    response = client.get(f"/users/{"thanosablls"}")
    assert response.status_code == 404


def test_edit_user(test_db):

    response = client.patch(
        f"/users/{1}",
        json={
            "name": "string",
            "username": "stringaasda",
            "bio": "string",
            "pfp_link": "string",
            "fav_genres": ["string"],
        },
    )
    assert response.status_code == 200


def test_edit_user_not_found():
    response = client.patch(
        f"/users/{999}",
        json={
            "name": "string",
            "username": "string",
            "bio": "string",
            "pfp_link": "string",
            "fav_genres": ["string"],
        },
    )
    assert response.status_code == 404


def test_edit_user_duplicate_username(test_db):
    test_user = User(
        name="test",
        username="anythings",
        bio="heyyy",
        email="test@mail.com",
        hash_password="blahblah",
        create_date=date.today(),
        fav_genres=["rock"],
    )
    test_db.add(test_user)
    test_db.commit()
    test_db.refresh(test_user)
    response = client.patch(
        f"/users/{1}",
        json={
            "name": "string",
            "username": "anythings",
            "bio": "string",
            "pfp_link": "string",
            "fav_genres": ["string"],
        },
    )
    assert response.status_code == 403


def test_edit_bio(test_db):
    user = test_db.query(User).filter(User.id == 1).first()
    response = client.patch(
        f"/users/{1}",
        json={
            "bio": "blah blah",
        },
    )
    test_db.refresh(user)

    assert response.status_code == 200
    assert user.username == "testusr"


def test_edit_user_empty(test_db):
    user = test_db.query(User).filter(User.id == 1).first()
    test_db.refresh(user)
    response = client.patch(
        f"/users/{1}",
        json={},
    )
    assert response.status_code == 200
    assert user.username == "testusr"


def test_delete_user(test_db):
    user = test_db.query(User).filter(User.id == 1).first()

    response = client.request(
        "DELETE", f"/users/{user.id}", json={"password": "string"}
    )
    assert response.status_code == 200


def test_delete_user_not_found(test_db):
    response = client.request("DELETE", f"/users/{9797}", json={"password": "string"})
    assert response.status_code == 404


def test_delete_user_incorrect_password(test_db):
    response = client.request("DELETE", f"/users/{1}", json={"password": "strings"})
    assert response.status_code == 401


def test_add_taste_entry(test_db):
    response = client.post(
        "/users/me/taste?category=top_songs",
        json={"mbid": "string", "rank": 3, "liked": False},
    )
    assert response.status_code == 200


def test_add_taste_entry_duplicate_mbid(test_db):
    entry = TasteEntry(
        mbid="hello", category="top_songs", rank=2, user_id=1, liked=True
    )
    test_db.add(entry)
    test_db.commit()
    response = client.post(
        "/users/me/taste?category=top_songs",
        json={"mbid": "hello", "rank": 3, "liked": False},
    )
    assert response.status_code == 403


def test_add_taste_entry_ivalid_data():
    response = client.post(
        "/users/me/taste?category=top_songs",
        json={"mbid": "string", "liked": True},
    )
    assert response.status_code == 422


def test_add_taste_entry_duplicate_rank(test_db):
    entry = TasteEntry(
        mbid="hellos", category="top_songs", rank=2, user_id=1, liked=True
    )
    test_db.add(entry)
    test_db.commit()
    response = client.post(
        "/users/me/taste?category=top_songs",
        json={"mbid": "hello", "rank": 2, "liked": False},
    )
    assert response.status_code == 403


def test_add_taste_song_limit(test_db):
    response = client.post(
        "/users/me/taste?category=top_songs",
        json={"mbid": "hello", "rank": 11, "liked": False},
    )
    assert response.status_code == 403


def test_add_entry_others_limit():
    response = client.post(
        "/users/me/taste?category=top_albums",
        json={"mbid": "hello", "rank": 4, "liked": False},
    )
    assert response.status_code == 403


def test_delete_taste_entry(test_db):
    entry = TasteEntry(
        mbid="hello", category="top_songs", rank=2, user_id=1, liked=True
    )
    test_db.add(entry)
    test_db.commit()
    test_db.refresh(entry)
    response = client.delete(f"/users/me/taste/{entry.id}")
    assert response.status_code == 200


def test_delete_entry_not_found():
    response = client.delete(f"/users/me/taste/{12}")
    assert response.status_code == 404


def test_get_user_entries(test_db):
    entry = TasteEntry(
        mbid="hello", category="top_songs", rank=2, user_id=1, liked=True
    )
    test_db.add(entry)
    test_db.commit()
    test_db.refresh(entry)
    response = client.get(f"/users/{1}/taste?category=top_songs")
    assert response.status_code == 200


def test_get_user_entries_not_found():
    response = client.get(f"/users/{1}/taste?category=top_songs")
    assert response.status_code == 404
