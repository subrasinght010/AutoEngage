from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Use SQLite for local development
DATABASE_URL = "sqlite+aiosqlite:///./agent.db"

# Async SQLAlchemy engine
async_engine = create_async_engine(DATABASE_URL, echo=True, future=True)

Base = declarative_base()

# Async session makerZ
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

# Dependency for getting a session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Function to initialize the database
async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
