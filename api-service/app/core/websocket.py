"""
WebSocket Manager
Manages WebSocket connections for real-time device status updates
"""

import asyncio
import json
from typing import Dict, Set, Any
from fastapi import WebSocket
import structlog

logger = structlog.get_logger()


class WebSocketManager:
    """Manages WebSocket connections and broadcasts device updates"""

    def __init__(self):
        # All connected clients
        self._connections: Set[WebSocket] = set()
        # Clients subscribed to specific device UUIDs
        self._device_subscriptions: Dict[str, Set[WebSocket]] = {}
        # Clients subscribed to all device updates
        self._global_subscribers: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Accept and register a WebSocket connection"""
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.debug("WebSocket connected", total=len(self._connections))

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection and all its subscriptions"""
        async with self._lock:
            self._connections.discard(websocket)
            self._global_subscribers.discard(websocket)
            for device_id in list(self._device_subscriptions.keys()):
                self._device_subscriptions[device_id].discard(websocket)
                if not self._device_subscriptions[device_id]:
                    del self._device_subscriptions[device_id]
        logger.debug("WebSocket disconnected", total=len(self._connections))

    async def subscribe_device(self, websocket: WebSocket, device_id: str):
        """Subscribe a client to updates for a specific device"""
        async with self._lock:
            if device_id not in self._device_subscriptions:
                self._device_subscriptions[device_id] = set()
            self._device_subscriptions[device_id].add(websocket)
        logger.debug("Subscribed to device", device_id=device_id)

    async def unsubscribe_device(self, websocket: WebSocket, device_id: str):
        """Unsubscribe a client from a specific device"""
        async with self._lock:
            if device_id in self._device_subscriptions:
                self._device_subscriptions[device_id].discard(websocket)
                if not self._device_subscriptions[device_id]:
                    del self._device_subscriptions[device_id]

    async def subscribe_all(self, websocket: WebSocket):
        """Subscribe a client to all device updates"""
        async with self._lock:
            self._global_subscribers.add(websocket)

    async def unsubscribe_all(self, websocket: WebSocket):
        """Unsubscribe a client from all device updates"""
        async with self._lock:
            self._global_subscribers.discard(websocket)

    async def broadcast_device_update(self, device_id: str, data: Dict[str, Any]):
        """Broadcast a device update to subscribed clients"""
        message = json.dumps({
            "type": "device_update",
            "device_id": device_id,
            "data": data,
        })

        targets: Set[WebSocket] = set()
        async with self._lock:
            targets.update(self._global_subscribers)
            if device_id in self._device_subscriptions:
                targets.update(self._device_subscriptions[device_id])

        disconnected = []
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            await self.disconnect(ws)

    async def broadcast_transmission_log(self, device_id: str, log_data: Dict[str, Any]):
        """Broadcast a transmission log event"""
        message = json.dumps({
            "type": "transmission_log",
            "device_id": device_id,
            "data": log_data,
        })

        targets: Set[WebSocket] = set()
        async with self._lock:
            targets.update(self._global_subscribers)
            if device_id in self._device_subscriptions:
                targets.update(self._device_subscriptions[device_id])

        disconnected = []
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            await self.disconnect(ws)

    async def handle_client_message(self, websocket: WebSocket, raw: str):
        """Handle incoming messages from a WebSocket client"""
        try:
            msg = json.loads(raw)
            action = msg.get("action")

            if action == "subscribe_device":
                device_id = msg.get("device_id")
                if device_id:
                    await self.subscribe_device(websocket, device_id)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "device_id": device_id,
                    }))

            elif action == "unsubscribe_device":
                device_id = msg.get("device_id")
                if device_id:
                    await self.unsubscribe_device(websocket, device_id)
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed",
                        "device_id": device_id,
                    }))

            elif action == "subscribe_all":
                await self.subscribe_all(websocket)
                await websocket.send_text(json.dumps({
                    "type": "subscribed_all",
                }))

            elif action == "unsubscribe_all":
                await self.unsubscribe_all(websocket)
                await websocket.send_text(json.dumps({
                    "type": "unsubscribed_all",
                }))

            elif action == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown action: {action}",
                }))

        except json.JSONDecodeError:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Invalid JSON",
            }))


# Singleton instance
ws_manager = WebSocketManager()
