"""
FastAPI Main Application
IoT-DevSim Agent Service — AI Assistant
"""

import time
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.clients.api_client import internal_api_client

# Setup structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    try:
        # Startup
        logger.info(
            "Starting IoT-DevSim Agent Service",
            version="1.0.0",
            environment=settings.ENVIRONMENT,
            llm_provider=settings.LLM_PROVIDER,
            llm_model=settings.LLM_MODEL,
        )

        # Verify LLM provider configuration
        from app.core.llm_provider import check_llm_health

        llm_status = await check_llm_health()
        if llm_status.get("status") != "healthy":
            logger.warning(
                "LLM provider not fully healthy at startup",
                llm_status=llm_status,
            )
        else:
            logger.info("LLM provider healthy", llm_status=llm_status)

        yield

        # Shutdown
        logger.info("Shutting down IoT-DevSim Agent Service")
        await internal_api_client.close()

    except Exception as e:
        logger.error("Agent service lifecycle error", error=str(e))
        raise


# Create FastAPI application
app = FastAPI(
    title="IoT-DevSim Agent Service",
    description="AI Assistant for IoT Device Simulation Platform",
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# ==========================================
# CORS Middleware
# ==========================================
cors_origins = []

if settings.is_development:
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ]
    for origin in settings.cors_origins_list:
        if origin not in cors_origins:
            cors_origins.append(origin)
else:
    cors_origins = settings.cors_origins_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "X-Requested-With",
        "Origin",
    ],
    max_age=600,
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Root-level health check for Docker healthcheck command."""
    return {
        "status": "healthy",
        "service": "agent-service",
        "version": "1.0.0",
        "timestamp": time.time(),
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "IoT-DevSim Agent Service",
        "version": "1.0.0",
        "docs": "/docs" if settings.is_development else "disabled",
        "health": "/health",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.AGENT_PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )
