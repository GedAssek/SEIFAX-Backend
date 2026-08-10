"""Fix remaining documents with annee_etude=None by inspecting them"""
from database.db import get_db, connect_db, close_db
import asyncio

async def fix_remaining():
    await connect_db()
    db = get_db()
    
    count = await db.documents.count_documents({"annee_etude": None})
    print(f"Docs still with annee_etude=None: {count}")
    
    # Get a sample
    async for doc in db.documents.find({"annee_etude": None}).limit(5):
        m = doc.get("matiere", "")
        print(f"  matiere={m!r}, titre={doc.get('titre','')[:40]!r}")
    
    # They're all 'ÉLECTRONIQUE FONDAMENTALES' (year 1)
    # Assign them annee_etude=1
    result = await db.documents.update_many(
        {"annee_etude": None},
        {"$set": {"annee_etude": 1}}
    )
    print(f"Updated {result.modified_count} remaining docs to annee_etude=1")
    
    # Verify
    docs1 = await db.documents.count_documents({"annee_etude": 1})
    docs2 = await db.documents.count_documents({"annee_etude": 2})
    docs3 = await db.documents.count_documents({"annee_etude": 3})
    docsN = await db.documents.count_documents({"annee_etude": None})
    print(f"\nFinal state: annee 1={docs1}, 2={docs2}, 3={docs3}, None={docsN}")
    
    await close_db()

asyncio.run(fix_remaining())
