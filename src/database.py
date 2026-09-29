from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

engine = create_engine("sqlite:///data.db", connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(autocommit=False, bind=engine, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
