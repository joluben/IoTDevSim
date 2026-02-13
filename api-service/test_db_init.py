import asyncio
from app.core.database import engine
from sqlalchemy import text

async def test():
    try:
        async with engine.begin() as conn:
            from app.core.database import Base
            # Import models to register them
            from app.models.dataset import Dataset
            await conn.run_sync(Base.metadata.create_all)
        print("Success")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
