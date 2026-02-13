"""
Health Check Endpoints
System health and monitoring endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import time
import psutil
from typing import Dict, Any

from app.core.database import get_db, check_database_health
from app.schemas.base import HealthCheck, HealthStatus

logger = structlog.get_logger()
router = APIRouter()


@router.get("/", response_model=HealthCheck)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthCheck:
    """
    Comprehensive health check endpoint
    
    Returns:
        Health status with detailed checks
    """
    checks = {}
    overall_status = HealthStatus.HEALTHY
    
    try:
        # Database health check
        db_healthy = await check_database_health()
        checks["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "response_time_ms": 0  # Could measure actual response time
        }
        
        if not db_healthy:
            overall_status = HealthStatus.UNHEALTHY
        
        # Memory usage check
        memory = psutil.virtual_memory()
        memory_usage_percent = memory.percent
        checks["memory"] = {
            "status": "healthy" if memory_usage_percent < 90 else "degraded" if memory_usage_percent < 95 else "unhealthy",
            "usage_percent": memory_usage_percent,
            "available_gb": round(memory.available / (1024**3), 2)
        }
        
        if memory_usage_percent > 95:
            overall_status = HealthStatus.UNHEALTHY
        elif memory_usage_percent > 90 and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        
        # CPU usage check
        cpu_percent = psutil.cpu_percent(interval=1)
        checks["cpu"] = {
            "status": "healthy" if cpu_percent < 80 else "degraded" if cpu_percent < 95 else "unhealthy",
            "usage_percent": cpu_percent
        }
        
        if cpu_percent > 95:
            overall_status = HealthStatus.UNHEALTHY
        elif cpu_percent > 80 and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        
        # Disk usage check
        disk = psutil.disk_usage('/')
        disk_usage_percent = (disk.used / disk.total) * 100
        checks["disk"] = {
            "status": "healthy" if disk_usage_percent < 85 else "degraded" if disk_usage_percent < 95 else "unhealthy",
            "usage_percent": round(disk_usage_percent, 2),
            "free_gb": round(disk.free / (1024**3), 2)
        }
        
        if disk_usage_percent > 95:
            overall_status = HealthStatus.UNHEALTHY
        elif disk_usage_percent > 85 and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        
    except Exception as e:
        logger.error("Health check error", error=str(e))
        overall_status = HealthStatus.UNHEALTHY
        checks["error"] = {"message": str(e)}
    
    return HealthCheck(
        status=overall_status,
        service="iot-devsim-api",
        version="2.0.0",
        checks=checks
    )


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Kubernetes readiness probe endpoint
    
    Returns:
        Simple ready/not ready status
    """
    try:
        # Check if database is accessible
        db_healthy = await check_database_health()
        
        if db_healthy:
            return {"status": "ready", "timestamp": time.time()}
        else:
            return {"status": "not ready", "reason": "database unavailable", "timestamp": time.time()}
    
    except Exception as e:
        logger.error("Readiness check error", error=str(e))
        return {"status": "not ready", "reason": str(e), "timestamp": time.time()}


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes liveness probe endpoint
    
    Returns:
        Simple alive status
    """
    return {"status": "alive", "timestamp": time.time()}