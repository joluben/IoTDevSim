"""
Transmission Control Endpoints
Control and monitor message transmission
"""

import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.transmission_manager import transmission_manager

router = APIRouter()


class DeviceNotifyRequest(BaseModel):
    """Request body for device notification"""
    reset_row_index: Optional[bool] = True


@router.get("/status")
async def get_transmission_status():
    """Get transmission service status"""
    stats = transmission_manager.get_stats()
    
    return {
        "running": transmission_manager.is_running(),
        "active_connections": transmission_manager.get_active_connection_count(),
        "total_messages": transmission_manager.get_total_message_count(),
        "statistics": {
            "total_messages": stats.total_messages,
            "successful_messages": stats.successful_messages,
            "failed_messages": stats.failed_messages,
            "bytes_transmitted": stats.bytes_transmitted,
            "uptime_seconds": round(time.time() - stats.start_time, 2) if stats.start_time else 0
        }
    }


@router.post("/start")
async def start_transmission():
    """Start transmission service"""
    if transmission_manager.is_running():
        raise HTTPException(status_code=400, detail="Transmission service already running")
    
    await transmission_manager.start()
    return {"message": "Transmission service started"}


@router.post("/stop")
async def stop_transmission():
    """Stop transmission service"""
    if not transmission_manager.is_running():
        raise HTTPException(status_code=400, detail="Transmission service not running")
    
    await transmission_manager.stop()
    return {"message": "Transmission service stopped"}


@router.post("/restart")
async def restart_transmission():
    """Restart transmission service"""
    if transmission_manager.is_running():
        await transmission_manager.stop()
    
    await transmission_manager.start()
    return {"message": "Transmission service restarted"}


@router.post("/devices/{device_id}/stop")
async def stop_device_transmission(device_id: str, body: DeviceNotifyRequest = DeviceNotifyRequest()):
    """Immediately stop transmission for a specific device"""
    await transmission_manager.remove_device(device_id, reset_row_index=body.reset_row_index)
    return {
        "message": f"Device {device_id} removed from active transmission",
        "row_index_reset": body.reset_row_index,
    }


@router.post("/devices/{device_id}/start")
async def start_device_transmission(device_id: str):
    """Immediately add/refresh a device into active transmission"""
    await transmission_manager.refresh_device(device_id)
    is_active = device_id in transmission_manager.active_devices
    return {
        "message": f"Device {device_id} {'added to' if is_active else 'not eligible for'} transmission",
        "active": is_active,
    }


@router.post("/devices/{device_id}/refresh")
async def refresh_device_transmission(device_id: str):
    """Force-refresh a device from DB state (add if transmitting, remove if not)"""
    await transmission_manager.refresh_device(device_id)
    is_active = device_id in transmission_manager.active_devices
    return {
        "message": f"Device {device_id} refreshed",
        "active": is_active,
    }
