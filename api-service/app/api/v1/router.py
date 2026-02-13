"""
API v1 Router
Main router for all API v1 endpoints
"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, devices, projects, connections, users, health, datasets

api_router = APIRouter()

# Authentication endpoints
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

# User management endpoints
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

# Device management endpoints
api_router.include_router(
    devices.router,
    prefix="/devices",
    tags=["devices"]
)

# Project management endpoints
api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["projects"]
)

# Dataset management endpoints
api_router.include_router(
    datasets.router,
    prefix="/datasets",
    tags=["datasets"]
)

# Connection management endpoints
api_router.include_router(
    connections.router,
    prefix="/connections",
    tags=["connections"]
)

# Health and monitoring endpoints
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)