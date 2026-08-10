import asyncio
from database.db import get_db, connect_db, close_db

async def main():
    await connect_db()
    db = get_db()
    
    docs_1 = await db.documents.count_documents({"annee_etude": 1})
    docs_2 = await db.documents.count_documents({"annee_etude": 2})
    docs_none = await db.documents.count_documents({"annee_etude": None})
    docs_str1 = await db.documents.count_documents({"annee_etude": "1"})
    docs_str2 = await db.documents.count_documents({"annee_etude": "2"})
    
    print(f"annee_etude = 1: {docs_1}")
    print(f"annee_etude = 2: {docs_2}")
    print(f"annee_etude = None: {docs_none}")
    print(f"annee_etude = '1': {docs_str1}")
    print(f"annee_etude = '2': {docs_str2}")
    
    await close_db()

if __name__ == "__main__":
    asyncio.run(main())
