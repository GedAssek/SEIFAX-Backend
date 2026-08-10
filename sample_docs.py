import asyncio
from database.db import get_db, connect_db, close_db

async def main():
    await connect_db()
    db = get_db()
    
    # Get a sample of documents to inspect their file_url
    cursor = db.documents.find({}).limit(5)
    docs = await cursor.to_list(length=5)
    
    for d in docs:
        print(f"Matiere: {d.get('matiere')}")
        print(f"file_url: {d.get('file_url')}")
        print(f"annee_etude: {d.get('annee_etude')}")
        print("---")
    
    await close_db()

if __name__ == "__main__":
    asyncio.run(main())
