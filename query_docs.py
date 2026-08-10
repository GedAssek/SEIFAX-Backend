import asyncio
from database.db import get_db, connect_db, close_db

async def main():
    await connect_db()
    db = get_db()
    cursor = db.documents.find({})
    docs = await cursor.to_list(length=100)
    print(f"Total documents: {len(docs)}")
    for d in docs:
        print(f"ID: {d.get('_id')}, Cycle: {d.get('cycle')}, Titre: {d.get('titre')}, AnneeEtude: {d.get('annee_etude')} (type: {type(d.get('annee_etude'))}), Matiere: {d.get('matiere')}")
    await close_db()

if __name__ == "__main__":
    asyncio.run(main())
