from fastapi.testclient import TestClient
import pytest
from src.main import app
from src.dependencies import get_current_user
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, get_db
from src.models import TasteEntry, User, Review, Connection
from datetime import date
from sqlalchemy.pool import StaticPool
from pwdlib import PasswordHash

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
    assert response.status_code == 409


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
        f"/users/me",
        json={
            "name": "string",
            "username": "stringaasda",
            "bio": "string",
            "pfp_link": "string",
            "fav_genres": ["string"],
        },
    )
    assert response.status_code == 200


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
        f"/users/me",
        json={
            "name": "string",
            "username": "anythings",
            "bio": "string",
            "pfp_link": "string",
            "fav_genres": ["string"],
        },
    )
    assert response.status_code == 409


def test_edit_bio(test_db):
    user = test_db.query(User).filter(User.id == 1).first()
    response = client.patch(
        f"/users/me",
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
        f"/users/me",
        json={},
    )
    assert response.status_code == 200
    assert user.username == "testusr"


def test_delete_user(test_db):
    response = client.request("DELETE", f"/users/testusr", json={"password": "string"})
    assert response.status_code == 200


def test_delete_user_not_found(test_db):
    response = client.request("DELETE", f"/users/jsdf", json={"password": "string"})
    assert response.status_code == 404


def test_delete_user_incorrect_password(test_db):
    response = client.request("DELETE", f"/users/testusr", json={"password": "strings"})
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
    assert response.status_code == 400


def test_add_taste_entry_multiple_user(test_db):
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
    entry = TasteEntry(
        mbid="hello", category="top_songs", rank=3, user_id=test_user.id, liked=True
    )
    test_db.add(entry)
    test_db.commit()
    response = client.post(
        "/users/me/taste?category=top_songs",
        json={"mbid": "hello", "rank": 3, "liked": True},
    )
    assert response.status_code == 200


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
    assert response.status_code == 400


def test_add_taste_song_limit(test_db):
    response = client.post(
        "/users/me/taste?category=top_songs",
        json={"mbid": "hello", "rank": 11, "liked": False},
    )
    assert response.status_code == 400


def test_add_entry_others_limit():
    response = client.post(
        "/users/me/taste?category=top_albums",
        json={"mbid": "hello", "rank": 4, "liked": False},
    )
    assert response.status_code == 400


def test_add_entry_rotation_song_limit_error(test_db):
    response = client.post(
        "/users/me/taste?category=rotation_song",
        json={"mbid": "hello", "rank": 7, "liked": False},
    )
    assert response.status_code == 400


def test_add_entry_rotation_song_limit_(test_db):
    response = client.post(
        "/users/me/taste?category=rotation_song",
        json={"mbid": "hello", "rank": 6, "liked": False},
    )
    assert response.status_code == 200


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
    response = client.get(f"/users/testusr/taste?category=top_songs")
    assert response.status_code == 200


def test_get_user_entries_not_found():
    response = client.get(f"/users/testusr/taste?category=top_songs")
    assert response.status_code == 404


def test_edit_entry_not_found():
    response = client.patch(
        f"/users/me/taste/{1}?category=top_songs",
        json={"mbid": "strisfsdfsdfng", "rank": 2, "liked": False},
    )
    assert response.status_code == 404


def test_edit_entry(test_db):
    entry = TasteEntry(
        mbid="hello", category="top_songs", rank=2, user_id=1, liked=True
    )
    test_db.add(entry)
    test_db.commit()
    test_db.refresh(entry)
    response = client.patch(
        f"/users/me/taste/{entry.id}?category=top_songs",
        json={"mbid": "strisfsdfsdfng", "rank": 3, "liked": False},
    )
    assert response.status_code == 200


def test_edit_entry_same_mbid(test_db):
    entry = TasteEntry(
        mbid="hello", category="top_songs", rank=2, user_id=1, liked=True
    )
    test_db.add(entry)
    test_db.commit()
    test_db.refresh(entry)
    response = client.patch(
        f"/users/me/taste/{entry.id}?category=top_songs",
        json={"mbid": "hello", "rank": 3, "liked": False},
    )
    assert response.status_code == 200


def test_edit_entry_same_rank(test_db):
    entry = TasteEntry(
        mbid="hello", category="top_songs", rank=2, user_id=1, liked=True
    )
    test_db.add(entry)
    test_db.commit()
    test_db.refresh(entry)
    response = client.patch(
        f"/users/me/taste/{entry.id}?category=top_songs",
        json={"rank": 2, "liked": False},
    )
    assert response.status_code == 200


def test_edit_entry_change_existing_rank(test_db):
    entry = TasteEntry(
        mbid="hello", category="top_songs", rank=1, user_id=1, liked=True
    )
    entry2 = TasteEntry(
        mbid="hellodd", category="top_songs", rank=2, user_id=1, liked=True
    )
    test_db.add(entry)
    test_db.add(entry2)
    test_db.commit()
    test_db.refresh(entry)
    response = client.patch(
        f"/users/me/taste/{entry.id}?category=top_songs",
        json={"rank": 2, "liked": False},
    )
    assert response.status_code == 409


def test_get_liked(test_db):
    entry = TasteEntry(
        mbid="hello", category="top_songs", rank=1, user_id=1, liked=True
    )
    entry2 = TasteEntry(
        mbid="hellodd", category="top_songs", rank=2, user_id=1, liked=True
    )
    test_db.add(entry)
    test_db.add(entry2)
    test_db.commit()
    response = client.get(f"/users/me/taste/liked")
    assert response.status_code == 200


def test_get_liked_none(test_db):
    response = client.get(f"/users/me/taste/liked")
    assert response.status_code == 200
    assert response.json() == {"message": "No liked songs"}


def test_edit_entry_one_field(test_db):
    entry = TasteEntry(
        mbid="hello", category="top_songs", rank=2, user_id=1, liked=True
    )
    test_db.add(entry)
    test_db.commit()
    test_db.refresh(entry)
    response = client.patch(
        f"/users/me/taste/{entry.id}?category=top_songs",
        json={"mbid": "strisfsdfsdfng"},
    )
    assert response.status_code == 200


def test_edit_entry_one_field_bool(test_db):
    entry = TasteEntry(
        mbid="hello", category="top_songs", rank=2, user_id=1, liked=False
    )
    test_db.add(entry)
    test_db.commit()
    test_db.refresh(entry)
    response = client.patch(
        f"/users/me/taste/{entry.id}?category=top_songs",
        json={"liked": True},
    )
    assert response.status_code == 200


def test_edit_entry_empty(test_db):
    entry = TasteEntry(
        mbid="hello", category="top_songs", rank=2, user_id=1, liked=True
    )
    test_db.add(entry)
    test_db.commit()
    test_db.refresh(entry)
    response = client.patch(
        f"/users/me/taste/{entry.id}?category=top_songs",
        json={},
    )
    assert response.status_code == 200
    assert entry.mbid == "hello"


def test_add_review():
    response = client.post(
        "/users/me/reviews",
        json={
            "review_str": "string",
            "rating": 10,
            "mbid": "str",
            "create_date": "2026-09-25",
        },
    )
    assert response.status_code == 200


def test_add_review_without_mbid():
    response = client.post(
        "/users/me/reviews",
        json={
            "review_str": "string",
            "rating": 10,
            "create_date": "2026-09-25",
        },
    )
    assert response.status_code == 422


def test_add_review_duplicate(test_db):
    review = Review(
        review_str="string",
        rating=7,
        user_id=1,
        mbid="heyheyhey",
        create_date=date.today(),
    )
    test_db.add(review)
    test_db.commit()
    response = client.post(
        "/users/me/reviews",
        json={
            "review_str": "blah blah",
            "rating": 7,
            "mbid": "heyheyhey",
            "create_date": "2026-09-09",
        },
    )
    assert response.status_code == 409


def test_add_review_rating_limit():
    response = client.post(
        "/users/me/reviews",
        json={
            "review_str": "string",
            "rating": 11,
            "mbid": "str",
            "create_date": "2026-09-25",
        },
    )
    assert response.status_code == 422


def test_add_review_invalid():
    response = client.post(
        "/users/me/reviews",
        json={
            "review_str": "string",
            "rating": 11,
            "user_id": 1,
            "mbid": "str",
        },
    )
    assert response.status_code == 422


def test_get_user_reviews_not_found():
    response = client.get(f"/users/testusr/reviews")
    assert response.status_code == 404


def test_get_user_reviews(test_db):
    review = Review(
        review_str="string",
        rating=7,
        user_id=1,
        mbid="heyheyhey",
        create_date=date.today(),
    )
    test_db.add(review)
    test_db.commit()

    response = client.get(f"/users/testusr/reviews")
    assert response.status_code == 200


def test_get_user_reviews_user_not_found():
    response = client.get(f"/users/jinglemster/reviews")
    assert response.status_code == 404


def test_get_album_reviews_not_found():
    response = client.get(f"/albums/hey/reviews")
    assert response.status_code == 404


def test_get_album_reviews(test_db):
    review = Review(
        review_str="string",
        rating=7,
        user_id=1,
        mbid="heyheyhey",
        create_date=date.today(),
    )
    test_db.add(review)
    test_db.commit()

    response = client.get("/albums/heyheyhey/reviews")
    assert response.status_code == 200


def test_edit_review_not_found():
    response = client.patch(
        f"/users/me/reviews/{1}",
        json={"review_str": "string", "rating": 10, "updated_date": "2026-09-26"},
    )
    assert response.status_code == 404


def test_edit_review_empty(test_db):
    review = Review(
        review_str="string",
        rating=7,
        user_id=1,
        mbid="heyheyhey",
        create_date=date.today(),
    )
    test_db.add(review)
    test_db.commit()
    test_db.refresh(review)
    response = client.patch(f"/users/me/reviews/{review.id}", json={})
    test_db.refresh(review)
    assert response.status_code == 200
    assert review.rating == 7


def test_edit_review_one_field(test_db):
    review = Review(
        review_str="string",
        rating=7,
        user_id=1,
        mbid="heyheyhey",
        create_date=date.today(),
    )
    test_db.add(review)
    test_db.commit()
    test_db.refresh(review)
    response = client.patch(f"/users/me/reviews/{review.id}", json={"rating": 10})
    test_db.refresh(review)
    assert response.status_code == 200
    assert review.rating == 10


def test_edit_review(test_db):
    review = Review(
        review_str="string",
        rating=7,
        user_id=1,
        mbid="heyheyhey",
        create_date=date.today(),
    )
    test_db.add(review)
    test_db.commit()
    test_db.refresh(review)
    response = client.patch(
        f"/users/me/reviews/{review.id}",
        json={"review_str": "string", "rating": 10},
    )
    test_db.refresh(review)
    assert response.status_code == 200
    assert review.updated_date == date.today()


def test_delete_review_not_found():
    response = client.delete(f"/users/me/reviews/{1}")
    assert response.status_code == 404


def test_delete_review(test_db):
    review = Review(
        review_str="string",
        rating=7,
        user_id=1,
        mbid="heyheyhey",
        create_date=date.today(),
    )
    test_db.add(review)
    test_db.commit()
    test_db.refresh(review)
    response = client.delete(f"/users/me/reviews/{review.id}")
    assert response.status_code == 200


def test_delete_review_unauthorized(test_db):
    review = Review(
        review_str="string",
        rating=7,
        user_id=99,
        mbid="heyheyhey",
        create_date=date.today(),
    )
    test_db.add(review)
    test_db.commit()
    test_db.refresh(review)
    response = client.delete(f"/users/me/reviews/{review.id}")
    assert response.status_code == 403


def test_send_connection(test_db):
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
    response = client.post(f"/connections/{test_user.id}")
    assert response.status_code == 200


def test_send_connection_not_found():
    response = client.post(f"/connections/{2}")
    assert response.status_code == 404


def test_send_connection_self():
    response = client.post(f"/connections/{1}")
    assert response.status_code == 400


def test_send_connection_existing(test_db):
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
    test_con = Connection(user_id1=1, user_id2=test_user.id)
    test_db.add(test_con)
    test_db.commit()
    response = client.post(f"/connections/{test_user.id}")
    assert response.status_code == 409


def test_accept_connection(test_db):
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
    test_con = Connection(user_id1=test_user.id, user_id2=1)
    test_db.add(test_con)
    test_db.commit()
    test_db.refresh(test_con)
    response = client.patch(f"/connections/{test_con.id}/accept")
    test_db.refresh(test_con)
    assert response.status_code == 200
    assert test_con.accepted == True


def test_accept_connecton_not_found():
    response = client.patch(f"/connections/{1}/accept")
    assert response.status_code == 404


def test_delete_connect_request_not_found():
    response = client.delete(f"/connections/{1}")
    assert response.status_code == 404


def test_delete_connection_not_acceped(test_db):
    test_con = Connection(user_id1=1, user_id2=67)
    test_db.add(test_con)
    test_db.commit()
    test_db.refresh(test_con)
    response = client.delete(f"/connections/{test_con.id}")
    assert response.status_code == 200


def test_delete_connection_acceped(test_db):
    test_con = Connection(
        user_id1=1, user_id2=67, accepted=True, connect_date=date.today()
    )
    test_db.add(test_con)
    test_db.commit()
    test_db.refresh(test_con)
    response = client.delete(f"/connections/{test_con.id}")
    assert response.status_code == 200


def test_get_connections(test_db):
    test_con = Connection(
        user_id1=1, user_id2=67, accepted=True, connect_date=date.today()
    )
    test_con2 = Connection(
        user_id1=6, user_id2=1, accepted=True, connect_date=date.today()
    )
    test_db.add(test_con)
    test_db.add(test_con2)
    test_db.commit()
    test_db.refresh(test_con)
    test_db.refresh(test_con2)
    response = client.get("/connections/me")
    assert response.status_code == 200


def test_get_connections_not_found():
    response = client.get("/connections/me")
    assert response.status_code == 200
    assert response.json() == []


def test_get_pending_connections_not_found():
    response = client.get("/connections/me/pending")
    assert response.status_code == 200
    assert response.json() == []


def test_get_pending_connections(test_db):
    test_con = Connection(user_id1=6, user_id2=1)
    test_db.add(test_con)
    test_db.commit()
    response = client.get("/connections/me/pending")
    assert response.status_code == 200


def test_get_sent_connections_not_found():
    response = client.get("/connections/me/sent")
    assert response.status_code == 200
    assert response.json() == []


def test_get_sent_connections(test_db):
    test_con = Connection(user_id1=1, user_id2=13)
    test_db.add(test_con)
    test_db.commit()
    response = client.get("/connections/me/sent")
    assert response.status_code == 200


def test_activity_not_found():
    response = client.get("/activity")
    assert response.status_code == 404


def test_activty(test_db):
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
    test_con = Connection(user_id1=1, user_id2=test_user.id, accepted=True)
    test_db.add(test_con)
    test_db.commit()
    test_db.refresh(test_con)
    review = Review(
        review_str="string",
        rating=7,
        user_id=test_user.id,
        mbid="heyheyhey",
        create_date=date.today(),
    )
    test_db.add(review)
    test_db.commit()
    response = client.get("/activity")
    assert response.status_code == 200
