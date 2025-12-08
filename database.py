from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker, declarative_base
)

DATABASEURL = "postgresql+psycopg://postgres:123456@localhost:5432/library_app"

engine = create_engine(DATABASEURL, echo=False, future=True, pool_size=5, max_overflow=10)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
