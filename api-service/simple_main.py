"""
Simple FastAPI Application for Testing
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import time
import uuid

# Create FastAPI application
app = FastAPI(
    title="IoT DevSim v2 API",
    description="IoT Device Simulation and Management Platform API",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "iot-devsim-api",
        "version": "2.0.0",
        "timestamp": time.time()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "IoT DevSim v2 API Service",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.post("/api/v1/auth/login")
async def login():
    """Mock login endpoint"""
    return {
        "access_token": "mock-jwt-token",
        "token_type": "bearer",
        "user": {
            "id": "1",
            "email": "test@example.com",
            "name": "Test User"
        }
    }

@app.post("/api/v1/auth/register")
async def register():
    """Mock register endpoint"""
    return {
        "message": "User registered successfully",
        "user": {
            "id": "1",
            "email": "test@example.com",
            "name": "Test User"
        }
    }

@app.get("/api/v1/users/me")
async def get_current_user():
    """Mock current user endpoint"""
    return {
        "id": "1",
        "email": "test@example.com",
        "name": "Test User",
        "is_active": True
    }

# In-memory storage for connections
connections_db = {}

class ConnectionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    protocol: str
    config: Dict[str, Any]
    is_active: Optional[bool] = True

@app.get("/api/v1/connections")
async def list_connections():
    """List all connections"""
    return {
        "items": list(connections_db.values()),
        "total": len(connections_db),
        "skip": 0,
        "limit": 100,
        "has_next": False,
        "has_prev": False
    }

@app.post("/api/v1/connections")
async def create_connection(connection: ConnectionCreate):
    """Create a new connection"""
    from datetime import datetime
    connection_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"
    connection_data = {
        "id": connection_id,
        "name": connection.name,
        "description": connection.description,
        "protocol": connection.protocol,
        "config": connection.config,
        "is_active": connection.is_active,
        "test_status": "untested",
        "last_tested": None,
        "test_message": None,
        "created_at": now,
        "updated_at": now
    }
    connections_db[connection_id] = connection_data
    return connection_data

@app.get("/api/v1/connections/{connection_id}")
async def get_connection(connection_id: str):
    """Get a connection by ID"""
    if connection_id not in connections_db:
        raise HTTPException(status_code=404, detail="Connection not found")
    return connections_db[connection_id]

@app.patch("/api/v1/connections/{connection_id}")
async def update_connection(connection_id: str, update_data: Dict[str, Any]):
    """Update a connection (enable/disable, etc.)"""
    from datetime import datetime
    if connection_id not in connections_db:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    connection = connections_db[connection_id]
    now = datetime.utcnow().isoformat() + "Z"
    
    # Update allowed fields
    if "is_active" in update_data:
        connection["is_active"] = update_data["is_active"]
    if "name" in update_data:
        connection["name"] = update_data["name"]
    if "description" in update_data:
        connection["description"] = update_data["description"]
    if "config" in update_data:
        connection["config"] = update_data["config"]
    
    connection["updated_at"] = now
    return connection

@app.delete("/api/v1/connections/{connection_id}")
async def delete_connection(connection_id: str):
    """Delete a connection"""
    if connection_id not in connections_db:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    del connections_db[connection_id]
    return {"message": "Connection deleted successfully"}

@app.post("/api/v1/connections/{connection_id}/test")
async def test_connection(connection_id: str):
    """Test a connection"""
    from datetime import datetime
    if connection_id not in connections_db:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    connection = connections_db[connection_id]
    now = datetime.utcnow().isoformat() + "Z"
    protocol = connection["protocol"]
    
    # Simulate successful test
    connection["test_status"] = "success"
    connection["last_tested"] = now
    connection["test_message"] = "Connection test successful"
    connection["updated_at"] = now
    
    # Build protocol-specific details
    details = {"protocol": protocol}
    
    if protocol == "mqtt":
        details.update({
            "broker": connection["config"].get("broker_url", ""),
            "port": connection["config"].get("port", 1883),
            "topic": connection["config"].get("topic", "")
        })
    elif protocol in ["http", "https"]:
        details.update({
            "endpoint": connection["config"].get("endpoint_url", ""),
            "method": connection["config"].get("method", "POST"),
            "auth_type": connection["config"].get("auth_type", "none")
        })
    elif protocol == "kafka":
        details.update({
            "brokers": connection["config"].get("bootstrap_servers", ""),
            "topic": connection["config"].get("topic", "")
        })
    
    return {
        "success": True,
        "message": "Connection test successful",
        "duration_ms": 150,
        "timestamp": now,
        "details": details
    }

@app.post("/api/v1/connections/export")
async def export_connections(export_request: Dict[str, Any]):
    """Export connections to JSON"""
    from datetime import datetime
    import base64
    
    connection_ids = export_request.get("connection_ids", [])
    sensitive_data_handling = export_request.get("sensitive_data_handling", "ENCRYPTED")
    
    # Get connections to export
    if connection_ids:
        connections_to_export = [connections_db[cid] for cid in connection_ids if cid in connections_db]
    else:
        connections_to_export = list(connections_db.values())
    
    # Handle sensitive data
    exported_connections = []
    for conn in connections_to_export:
        conn_copy = conn.copy()
        if sensitive_data_handling == "MASKED":
            # Mask sensitive fields
            if "config" in conn_copy:
                config = conn_copy["config"].copy()
                if "password" in config:
                    config["password"] = "***MASKED***"
                if "client_key" in config:
                    config["client_key"] = "***MASKED***"
                conn_copy["config"] = config
        exported_connections.append(conn_copy)
    
    return {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "count": len(exported_connections),
        "connections": exported_connections
    }

@app.post("/api/v1/connections/import")
async def import_connections(import_request: Dict[str, Any]):
    """Import connections from JSON"""
    from datetime import datetime
    
    connections_data = import_request.get("connections", [])
    strategy = import_request.get("strategy", "SKIP")
    
    results = {
        "total": len(connections_data),
        "successful": 0,
        "failed": 0,
        "skipped": 0,
        "items": []
    }
    
    for conn_data in connections_data:
        conn_name = conn_data.get("name", "Unknown")
        
        # Check if connection with same name exists
        existing_conn = None
        for cid, conn in connections_db.items():
            if conn["name"] == conn_name:
                existing_conn = (cid, conn)
                break
        
        if existing_conn and strategy == "SKIP":
            results["skipped"] += 1
            results["items"].append({
                "name": conn_name,
                "status": "skipped",
                "message": "Connection already exists"
            })
        elif existing_conn and strategy == "OVERWRITE":
            # Update existing connection
            cid, _ = existing_conn
            now = datetime.utcnow().isoformat() + "Z"
            connections_db[cid].update({
                "description": conn_data.get("description"),
                "protocol": conn_data.get("protocol"),
                "config": conn_data.get("config"),
                "is_active": conn_data.get("is_active", True),
                "updated_at": now
            })
            results["successful"] += 1
            results["items"].append({
                "name": conn_name,
                "status": "success",
                "message": "Connection updated"
            })
        elif existing_conn and strategy == "RENAME":
            # Create with new name
            counter = 1
            new_name = f"{conn_name} ({counter})"
            while any(conn["name"] == new_name for conn in connections_db.values()):
                counter += 1
                new_name = f"{conn_name} ({counter})"
            
            connection_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat() + "Z"
            new_conn = {
                "id": connection_id,
                "name": new_name,
                "description": conn_data.get("description"),
                "protocol": conn_data.get("protocol"),
                "config": conn_data.get("config"),
                "is_active": conn_data.get("is_active", True),
                "test_status": "untested",
                "last_tested": None,
                "test_message": None,
                "created_at": now,
                "updated_at": now
            }
            connections_db[connection_id] = new_conn
            results["successful"] += 1
            results["items"].append({
                "name": new_name,
                "status": "success",
                "message": f"Connection created with new name"
            })
        else:
            # Create new connection
            connection_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat() + "Z"
            new_conn = {
                "id": connection_id,
                "name": conn_name,
                "description": conn_data.get("description"),
                "protocol": conn_data.get("protocol"),
                "config": conn_data.get("config"),
                "is_active": conn_data.get("is_active", True),
                "test_status": "untested",
                "last_tested": None,
                "test_message": None,
                "created_at": now,
                "updated_at": now
            }
            connections_db[connection_id] = new_conn
            results["successful"] += 1
            results["items"].append({
                "name": conn_name,
                "status": "success",
                "message": "Connection created"
            })
    
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("simple_main:app", host="0.0.0.0", port=8000, reload=True)
