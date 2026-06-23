"""
Database Configuration and Session Management
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# Base class for all models
class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db_session() -> AsyncSession:
    """
    Dependency function to get database session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database - create all tables.
    Must import models to ensure they are registered with Base.
    """
    # Import models to ensure they are registered
    from app.models import event, memory, evolution, governance, graph, frag, evaluation, user

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)