from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

engine = create_engine("sqlite:///data.db", connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


Session = sessionmaker(autocommit=False, bind=engine, autoflush=False)


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
