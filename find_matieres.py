import asyncio
from database.db import get_db, connect_db, close_db

async def main():
    await connect_db()
    db = get_db()
    
    matieres = await db.documents.distinct("matiere")
    
    keywords = ["ATN", "MAINTE", "MTO", "SATELL", "ANTEN", "EMISS", "RECEP", "RESEAU", "CNS", "ATM"]
    
    matches = []
    for m in matieres:
        m_upper = m.upper() if m else ""
        if any(kw in m_upper for kw in keywords):
            matches.append(m)
            
    print(f"Matched matieres: {matches}")
    
    await close_db()

if __name__ == "__main__":
    asyncio.run(main())
