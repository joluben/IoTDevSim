"""Update dataset status to ready directly in the database."""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import engine

async def fix():
    async with AsyncSession(engine) as db:
        r = await db.execute(text(
            "UPDATE datasets SET status = 'READY' WHERE name = 'Temperature Readings' RETURNING id, name, status"
        ))
        row = r.fetchone()
        if row:
            print(f"Updated: {row[1]} -> {row[2]}")
            await db.commit()

asyncio.run(fix())
