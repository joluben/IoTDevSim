"""Quick test to debug the devices list endpoint."""
import asyncio
from app.core.database import get_db, engine
from app.services.device import device_service
from app.schemas.device import DeviceFilterParams
from sqlalchemy.ext.asyncio import AsyncSession

async def test():
    async with AsyncSession(engine) as db:
        try:
            filters = DeviceFilterParams(skip=0, limit=10)
            devices, total = await device_service.list_devices(db, filters)
            print(f"OK: {total} devices found")
            for d in devices:
                print(f"  - {d.name} ({d.device_id})")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"ERROR: {e}")

asyncio.run(test())
