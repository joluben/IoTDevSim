"""
Database Configuration for Transmission Service
Uses standalone models (not shared with api-service)
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
import structlog

from app.core.config import settings, DATABASE_CONFIG
from app.models import Base, Device, Connection, TransmissionLog

logger = structlog.get_logger()

# Create async engine with optimized settings for transmission workloads
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    **DATABASE_CONFIG,
    poolclass=AsyncAdaptedQueuePool,
    # Transmission service specific optimizations
    connect_args={
        "server_settings": {
            "jit": "off",
            "application_name": "iot-devsim-transmission",
        }
    }
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# Database dependency
async def get_db() -> AsyncSession:
    """Database session dependency"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


from sqlalchemy import text

# Health check function
async def check_database_health() -> bool:
    """Check database connectivity"""
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False
