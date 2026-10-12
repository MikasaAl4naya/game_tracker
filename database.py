import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

_user = os.getenv("POSTGRES_USER", "admin")
_password = os.getenv("POSTGRES_PASSWORD", "password123")
_host = os.getenv("POSTGRES_HOST", "db")
_db_name = os.getenv("POSTGRES_DB", "tracker_db")

SYNC_DB_URL = f"postgresql://{_user}:{_password}@{_host}/{_db_name}"
ASYNC_DB_URL = f"postgresql+asyncpg://{_user}:{_password}@{_host}/{_db_name}"

sync_engine = create_engine(SYNC_DB_URL, pool_pre_ping=True)
engine = create_async_engine(ASYNC_DB_URL, echo=False)

SyncSessionLocal = sessionmaker(bind=sync_engine)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
