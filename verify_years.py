"""Vérification: ce que voit un élève de 2ème année"""
from database.db import get_db, connect_db
import asyncio

async def check():
    await connect_db()
    db = get_db()
    
    # Simulate what 2nd year student sees: annee_etude=2 OR None
    query = {"$or": [{"annee_etude": 2}, {"annee_etude": None}]}
    count = await db.documents.count_documents(query)
    print(f"2ème année voit: {count} documents (attendu: 263)")
    
    # 1st year
    query1 = {"$or": [{"annee_etude": 1}, {"annee_etude": None}]}
    count1 = await db.documents.count_documents(query1)
    print(f"1ère année voit: {count1} documents (attendu: 384)")
    
    # 3rd year
    query3 = {"$or": [{"annee_etude": 3}, {"annee_etude": None}]}
    count3 = await db.documents.count_documents(query3)
    print(f"3ème année voit: {count3} documents (attendu: 320)")

asyncio.run(check())
