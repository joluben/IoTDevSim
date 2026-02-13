"""
Statistics Endpoints for Transmission Service
"""

from fastapi import APIRouter
from app.services.transmission_manager import transmission_manager

router = APIRouter()


@router.get("/")
async def get_stats():
    stats = transmission_manager.get_stats()
    return {
        "running": transmission_manager.is_running(),
        "active_connections": transmission_manager.get_active_connection_count(),
        "total_messages": transmission_manager.get_total_message_count(),
        "successful_messages": stats.successful_messages,
        "failed_messages": stats.failed_messages,
        "bytes_transmitted": stats.bytes_transmitted,
    }
