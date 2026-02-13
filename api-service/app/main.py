"""
FastAPI Main Application
IoTDevSim API Service
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import structlog
from contextlib import asynccontextmanager
from sqlalchemy import text

from app.core.simple_config import settings
from app.core.database import engine, Base
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.logging import LoggingMiddleware

# Setup structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    try:
        # Startup
        logger.info("Starting IoTDevSim API Service", version="1.0.0")
        
        # Create database tables
        async with engine.begin() as conn:
            # Import models to ensure they are registered
            from app.models import device, project, connection, transmission_log, dataset
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
        
        yield
        
        # Shutdown
        logger.info("Shutting down IoTDevSim API Service")
        await engine.dispose()
    except Exception as e:
        logger.error("Startup failed", error=str(e))
        import traceback
        traceback.print_exc()
        raise e


# Create FastAPI application
app = FastAPI(
    title="IoTDevSim API",
    description="IoT Device Simulation and Management Platform API",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# Add security middlewares
app.add_middleware(SecurityHeadersMiddleware)
from app.middleware.security import RateLimitMiddleware, RequestValidationMiddleware
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestValidationMiddleware)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Add CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add trusted host middleware for production
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Include WebSocket router
from app.api.v1.endpoints.ws import router as ws_router
app.include_router(ws_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and load balancers"""
    try:
        # Test database connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "service": "iotdevsim-api",
            "version": "1.0.0",
            "timestamp": time.time(),
            "database": "connected"
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "iotdevsim-api",
                "version": "1.0.0",
                "timestamp": time.time(),
                "error": str(e)
            }
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "IoTDevSim API Service",
        "version": "1.0.0",
        "docs": "/docs" if settings.ENVIRONMENT == "development" else "disabled",
        "health": "/health"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower()
    )
