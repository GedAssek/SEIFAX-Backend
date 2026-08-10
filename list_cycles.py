import asyncio
from database.db import get_db, connect_db, close_db

async def main():
    await connect_db()
    db = get_db()
    
    cycles = await db.documents.distinct("cycle")
    print(f"Distinct cycles in DB: {cycles}")
    
    await close_db()

if __name__ == "__main__":
    asyncio.run(main())
