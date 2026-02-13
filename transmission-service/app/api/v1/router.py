"""
Transmission Service API v1 Router
Main router for transmission service endpoints
"""

from fastapi import APIRouter
from app.api.v1.endpoints import transmission, stats

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(transmission.router, prefix="/transmission", tags=["transmission"])
api_router.include_router(stats.router, prefix="/stats", tags=["statistics"])
