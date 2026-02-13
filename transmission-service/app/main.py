"""
FastAPI Transmission Service
IoTDevSim Message Transmission and Simulation Service
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import structlog
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, check_database_health
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.services.transmission_manager import transmission_manager

# Setup structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting IoTDevSim Transmission Service", version="1.0.0")
    
    # Start transmission manager
    await transmission_manager.start()
    
    logger.info("Transmission service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down IoTDevSim Transmission Service")
    
    # Stop transmission manager
    await transmission_manager.stop()
    
    # Close database connections
    await engine.dispose()


# Create FastAPI application
app = FastAPI(
    title="IoTDevSim Transmission Service",
    description="IoT Device Message Transmission and Simulation Service",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# Add CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and load balancers"""
    try:
        # Test database connection
        db_healthy = await check_database_health()
        
        # Check transmission manager status
        transmission_healthy = transmission_manager.is_running()
        
        if db_healthy and transmission_healthy:
            return {
                "status": "healthy",
                "service": "iotdevsim-transmission",
                "version": "1.0.0",
                "timestamp": time.time(),
                "database": "connected",
                "transmission_manager": "running",
                "active_connections": transmission_manager.get_active_connection_count(),
                "total_messages": transmission_manager.get_total_message_count()
            }
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "service": "iotdevsim-transmission",
                    "version": "1.0.0",
                    "timestamp": time.time(),
                    "database": "connected" if db_healthy else "disconnected",
                    "transmission_manager": "running" if transmission_healthy else "stopped"
                }
            )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "iotdevsim-transmission",
                "version": "1.0.0",
                "timestamp": time.time(),
                "error": str(e)
            }
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "IoTDevSim Transmission Service",
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
        port=8001,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower()
    )
