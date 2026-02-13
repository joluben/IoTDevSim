
import asyncio
import logging
from app.main import app, lifespan

# Configure logging to stdout
logging.basicConfig(level=logging.INFO)

async def test():
    print("Testing lifespan...")
    try:
        async with lifespan(app):
            print("Lifespan yielded successfully.")
            await asyncio.sleep(1)
    except Exception as e:
        print(f"Lifespan failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
