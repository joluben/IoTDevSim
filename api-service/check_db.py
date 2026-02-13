import asyncio
from app.core.database import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as c:
        r = await c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='devices' ORDER BY ordinal_position"))
        cols = [row[0] for row in r.fetchall()]
        print("Device columns:", cols)
        
        # Check if device_datasets table exists
        r2 = await c.execute(text("SELECT table_name FROM information_schema.tables WHERE table_name='device_datasets'"))
        tables = [row[0] for row in r2.fetchall()]
        print("device_datasets table exists:", len(tables) > 0)

asyncio.run(check())
