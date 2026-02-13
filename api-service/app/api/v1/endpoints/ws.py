"""
WebSocket Endpoint
Real-time device status and transmission updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

from app.core.websocket import ws_manager

logger = structlog.get_logger()
router = APIRouter()


@router.websocket("/ws/devices")
async def device_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time device updates.

    Client messages (JSON):
      {"action": "subscribe_device", "device_id": "<uuid>"}
      {"action": "unsubscribe_device", "device_id": "<uuid>"}
      {"action": "subscribe_all"}
      {"action": "unsubscribe_all"}
      {"action": "ping"}

    Server messages (JSON):
      {"type": "device_update", "device_id": "...", "data": {...}}
      {"type": "transmission_log", "device_id": "...", "data": {...}}
      {"type": "subscribed", "device_id": "..."}
      {"type": "pong"}
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            await ws_manager.handle_client_message(websocket, raw)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        await ws_manager.disconnect(websocket)
