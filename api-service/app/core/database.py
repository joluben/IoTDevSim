"""
Database Configuration and Session Management
Optimized for IoT workloads with connection pooling
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy import event, text
import structlog

from app.core.simple_config import settings, DATABASE_CONFIG

logger = structlog.get_logger()

# Create async engine with optimized settings for IoT workloads
database_url = settings.DATABASE_URL
if "postgresql://" in database_url:
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

engine_kwargs = {
    **DATABASE_CONFIG,
}
    
# Only add connect_args for PostgreSQL
if "postgresql" in database_url:
    engine_kwargs["connect_args"] = {
        "server_settings": {
            "jit": "off",  # Disable JIT for consistent performance
            "application_name": "iot-devsim-api",
        }
    }

engine = create_async_engine(
    database_url,
    **engine_kwargs
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # Manual flush control for better performance
)

# Create declarative base
Base = declarative_base()


# Database dependency for FastAPI
async def get_db() -> AsyncSession:
    """
    Database session dependency for FastAPI endpoints
    Ensures proper session cleanup and error handling
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Connection event listeners for monitoring
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set connection-level pragmas for PostgreSQL optimization"""
    if hasattr(dbapi_connection, 'execute'):
        # Set connection-specific optimizations
        cursor = dbapi_connection.cursor()
        
        # Optimize for write-heavy IoT workloads
        cursor.execute("SET synchronous_commit = off")  # Faster writes, slight durability trade-off
        cursor.execute("SET wal_buffers = '16MB'")      # Larger WAL buffers
        cursor.execute("SET checkpoint_segments = 32")   # More checkpoint segments
        cursor.execute("SET effective_io_concurrency = 200")  # SSD optimization
        
        cursor.close()


@event.listens_for(engine.sync_engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout for monitoring"""
    logger.debug("Database connection checked out", connection_id=id(dbapi_connection))


@event.listens_for(engine.sync_engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log connection checkin for monitoring"""
    logger.debug("Database connection checked in", connection_id=id(dbapi_connection))


# Health check function
async def check_database_health() -> bool:
    """
    Check database connectivity and basic functionality
    Used by health check endpoints
    """
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False


# Database initialization
async def init_database():
    """
    Initialize database tables and indexes
    Called during application startup
    """
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            from app.models import device, project, connection, transmission_log
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise


# Cleanup function
async def close_database():
    """
    Close database connections
    Called during application shutdown
    """
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Error closing database connections", error=str(e))
