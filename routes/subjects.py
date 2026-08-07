"""
LEFAXEUR - Routes Sujets (Cycles et Matières)
GET /api/subjects → Retourne tous les cycles et leurs matières
"""
from fastapi import APIRouter, Depends
from database.db import get_db
from routes.auth import get_current_user

router = APIRouter(prefix="/subjects", tags=["Matières & Cycles"])


@router.get("/")
async def get_subjects(_: dict = Depends(get_current_user)):
    db = get_db()
    cursor = db.subjects.find({}, {"_id": 0})
    results = []
    async for doc in cursor:
        results.append(doc)
    return results
