from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from src.config import settings

engine = create_engine(settings.DATABASE_URL)


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(autocommit=False, bind=engine, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
