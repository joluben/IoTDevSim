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
from app.core.database import AsyncSessionLocal, engine, Base
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware
from app.middleware.logging import LoggingMiddleware
from app.services.bootstrap_admin import ensure_bootstrap_admin_exists

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
            from app.models import connection, dataset, device, project, transmission_log, user
            await conn.run_sync(Base.metadata.create_all)

        # Ensure bootstrap admin exists (idempotent)
        async with AsyncSessionLocal() as session:
            await ensure_bootstrap_admin_exists(session)
        
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

# ==========================================
# CORS Middleware - MUST be added FIRST
# ==========================================
# CORS must be configured before any security middleware
# to ensure preflight requests are handled correctly

# Build CORS origins list
cors_origins = []

if settings.ENVIRONMENT == "development":
    # In development: allow common frontend development ports
    # and any additional origins from CORS_ORIGINS env var
    cors_origins = [
        "http://localhost:3000",      # React default
        "http://localhost:5173",      # Vite default
        "http://localhost:5174",      # Vite alternative
        "http://localhost:5175",      # Vite alternative
        "http://localhost:5176",      # Vite alternative
        "http://127.0.0.1:3000",      # React default (IP)
        "http://127.0.0.1:5173",      # Vite default (IP)
        "http://127.0.0.1:5174",      # Vite alternative (IP)
        "http://127.0.0.1:5175",      # Vite alternative (IP)
        "http://127.0.0.1:5176",      # Vite alternative (IP)
    ]
    # Add any custom origins from env (for Docker, external tools, etc.)
    if settings.CORS_ORIGINS:
        for origin in settings.CORS_ORIGINS:
            if origin not in cors_origins:
                cors_origins.append(origin)
else:
    # In production: use only explicitly configured origins
    cors_origins = settings.CORS_ORIGINS if settings.CORS_ORIGINS else []

logger.info(f"Configuring CORS for environment: {settings.ENVIRONMENT}")
logger.info(f"Allowed origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,  # Required for JWT authentication
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "X-Requested-With",
        "X-CSRF-Token",
        "Origin",
    ],
    expose_headers=["X-Total-Count"],  # For pagination headers
    max_age=600,  # Cache preflight requests for 10 minutes
)

# ==========================================
# Security Middlewares (after CORS)
# ==========================================
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

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
