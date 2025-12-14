from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Check if using SQLite
is_sqlite = "sqlite" in settings.DATABASE_URL.lower()

if is_sqlite:
    # Use synchronous engine for SQLite
    engine = create_engine(
        settings.DATABASE_URL.replace("sqlite:///", "sqlite:///"),
        pool_pre_ping=True,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )
else:
    # Use async engine for PostgreSQL
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.DEBUG
    )
    AsyncSessionLocal = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

# Base model
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    if is_sqlite:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    else:
        # For async database, we need to return an async function
        # This will be handled differently in the main app
        raise NotImplementedError("Async database requires async dependency injection")


async def init_db():
    """Initialize database tables"""
    if is_sqlite:
        Base.metadata.create_all(bind=engine)
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    if is_sqlite:
        engine.dispose()
    else:
        await engine.dispose()
