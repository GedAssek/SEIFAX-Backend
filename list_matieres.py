import asyncio
from database.db import get_db, connect_db, close_db

async def main():
    await connect_db()
    db = get_db()
    
    matieres = await db.documents.distinct("matiere")
    print(f"Distinct matieres in DB: {matieres}")
    
    await close_db()

if __name__ == "__main__":
    asyncio.run(main())
