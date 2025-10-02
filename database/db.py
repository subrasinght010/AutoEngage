from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# SQLite DB path
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./mydatabase.db"
)

# Async engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Async session
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base model
Base = declarative_base()

# Initialize tables
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Function to initialize the database
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
