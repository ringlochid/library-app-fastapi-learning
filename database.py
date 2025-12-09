import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_SYNC_URL = os.getenv(
    "DATABASE_SYNC_URL",
    os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:123456@localhost:5432/library_app",
    ),
)
DATABASE_ASYNC_URL = os.getenv(
    "DATABASE_ASYNC_URL",
    "postgresql+asyncpg://postgres:123456@localhost:5432/library_app",
)

sync_engine = create_engine(
    DATABASE_SYNC_URL, echo=False, future=True, pool_size=5, max_overflow=10
)
async_engine = create_async_engine(
    DATABASE_ASYNC_URL, echo=False, future=True, pool_size=5, max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, autoflush=False, expire_on_commit=False
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    async with AsyncSessionLocal() as db:
        yield db
