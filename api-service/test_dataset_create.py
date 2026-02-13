"""Debug dataset creation."""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import engine
from app.schemas.dataset import DatasetCreate, DatasetColumnCreate

async def test():
    async with AsyncSession(engine) as db:
        try:
            create_data = DatasetCreate(
                name="Temperature Readings",
                description="Sample temperature data for testing",
                source="generated",
                tags=["temperature", "test"],
                columns=[
                    DatasetColumnCreate(name="temperature", data_type="float", position=0),
                    DatasetColumnCreate(name="humidity", data_type="float", position=1),
                    DatasetColumnCreate(name="timestamp", data_type="string", position=2),
                ]
            )
            from app.services.dataset import dataset_service
            ds = await dataset_service.create_dataset(db, create_data)
            print(f"OK: {ds.name} ({ds.id})")
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(test())
