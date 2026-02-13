"""Debug the devices endpoint by calling the service directly with full traceback."""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import engine
from app.schemas.device import DeviceFilterParams, DeviceCreate, DeviceSummaryResponse
from app.services.device import device_service
from app.repositories.device import device_repository

async def test_list():
    print("=== Testing list_devices ===")
    async with AsyncSession(engine) as db:
        try:
            filters = DeviceFilterParams(skip=0, limit=10)
            devices, total = await device_service.list_devices(db, filters)
            print(f"list_devices OK: {total} devices")
            
            # Now test enrichment like the endpoint does
            for device in devices:
                count = await device_repository.get_dataset_count(db, device.id)
                summary = DeviceSummaryResponse.model_validate(device, from_attributes=True)
                summary.dataset_count = count
                summary.has_dataset = count > 0
                print(f"  enriched: {summary.name}")
        except Exception as e:
            import traceback
            traceback.print_exc()

async def test_create():
    print("\n=== Testing create_device ===")
    async with AsyncSession(engine) as db:
        try:
            create_data = DeviceCreate(name="Debug Sensor", device_type="sensor")
            device = await device_service.create_device(db, create_data)
            print(f"create_device OK: {device.name} ({device.device_id})")
            
            # Test enrichment
            count = await device_repository.get_dataset_count(db, device.id)
            print(f"  dataset_count: {count}")
            
            from app.schemas.device import DeviceResponse
            resp = DeviceResponse.model_validate(device, from_attributes=True)
            resp.dataset_count = count
            resp.has_dataset = count > 0
            print(f"  response model OK: {resp.name}")
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(test_list())
asyncio.run(test_create())
