from fastapi.testclient import TestClient
import pytest
from src.main import app, get_current_user
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, get_db
from src.models import TasteEntry, User, Review, Connection
from datetime import date
from sqlalchemy.pool import StaticPool

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
        username="anythingss",
        email="test@test.com",
        hash_password="fake",
        create_date=date.today(),
        fav_genres=["pop", "rock"],
    )


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture
def test_db():
    db = TestingSession()
    yield db
    db.query(TasteEntry).delete()
    db.query(Review).delete()
    db.commit()
    db.close()


@pytest.fixture(autouse=True)
def seed_test_user():
    db = TestingSession()
    user = User(
        name="amm",
        username="anythingss",
        email="test@test.com",
        hash_password="fake",
        create_date=date.today(),
        fav_genres=["pop", "rock"],
    )
    db.add(user)
    db.commit()
    db.close()


def test_root():
    response = client.get("/")
    assert response.status_code == 200


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
                "username": "anythingss",
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


def test_get_me(seed_test_user):
    response = client.get("/users/me")
    assert response.status_code == 200


def test_get_user_by_username():
    response = client.get(f"/users/{"anythingss"}")
    assert response.status_code == 200


def test_get_user_by_username_not_found():
    response = client.get(f"/users/{"thanosablls"}")
    assert response.status_code == 404
