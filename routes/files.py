"""Authenticated delivery of uploaded files."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from database.db import get_db
from routes.auth import get_current_user

router = APIRouter(prefix="/files", tags=["Fichiers"])
UPLOAD_ROOT = Path("uploads").resolve()
COLLECTIONS = {"documents": "documents", "epreuves": "epreuves", "infos": "infos"}


def _student_can_read_info(user: dict, info: dict) -> bool:
    if user.get("role") != "student":
        return True
    cycle = info.get("cycle", "Général")
    if cycle not in {"Général", "General", user.get("cycle")}:
        return False
    targeted_year = info.get("annee_etude")
    return targeted_year is None or targeted_year == user.get("annee")


@router.get("/{category}/{filename}")
async def download_file(
    category: str,
    filename: str,
    current_user: dict = Depends(get_current_user),
):
    if category not in COLLECTIONS or Path(filename).name != filename:
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    db = get_db()
    if category == "infos":
        record = await db.infos.find_one({"file_url": {"$in": [
            f"/api/files/infos/{filename}", f"/uploads/infos/{filename}"
        ]}})
        if not record or not _student_can_read_info(current_user, record):
            raise HTTPException(status_code=404, detail="Fichier introuvable")
    else:
        record = await db[COLLECTIONS[category]].find_one({"file_name": filename})
        if not record:
            raise HTTPException(status_code=404, detail="Fichier introuvable")

    path = (UPLOAD_ROOT / category / filename).resolve()
    if UPLOAD_ROOT not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(path)
