"""
LEFAXEUR - Routes Épreuves
GET    /api/epreuves          → Lister (avec filtres)
POST   /api/epreuves          → Ajouter (Admin seulement)
DELETE /api/epreuves/{id}     → Supprimer (Admin seulement)
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional
import os, shutil

from database.db import get_db
from routes.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/epreuves", tags=["Épreuves"])

UPLOAD_DIR = "uploads/epreuves"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def serialize_epreuve(doc: dict) -> dict:
    """Convertit un document MongoDB en dict JSON-compatible."""
    return {
        "id": str(doc["_id"]),
        "matiere": doc["matiere"],
        "cycle": doc["cycle"],
        "annee": doc["annee"],
        "description": doc.get("description", ""),
        "file_url": f"/uploads/epreuves/{doc['file_name']}",
        "created_at": doc.get("created_at", "")
    }


# ─── GET /api/epreuves ───────────────────────────────────────────────────────
@router.get("/")
async def list_epreuves(
    cycle: Optional[str] = Query(None),
    matiere: Optional[str] = Query(None),
    annee: Optional[int] = Query(None),
    _: dict = Depends(get_current_user)  # Authentification requise
):
    db = get_db()
    query = {}
    if cycle:
        query["cycle"] = cycle
    if matiere:
        query["matiere"] = {"$regex": matiere, "$options": "i"}
    if annee:
        query["annee"] = annee

    cursor = db.epreuves.find(query).sort("created_at", -1)
    results = []
    async for doc in cursor:
        results.append(serialize_epreuve(doc))
    return results


# ─── POST /api/epreuves ──────────────────────────────────────────────────────
@router.post("/", status_code=201)
async def add_epreuve(
    matiere: str = Form(...),
    cycle: str = Form(...),
    annee: int = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    admin: dict = Depends(get_admin_user)  # Admin seulement
):
    # Vérifier que c'est bien un PDF
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")

    db = get_db()

    # Sauvegarder le fichier
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = f"{cycle}_{matiere}_{annee}_{timestamp}.pdf".replace(" ", "_")
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    doc = {
        "matiere": matiere,
        "cycle": cycle,
        "annee": annee,
        "description": description,
        "file_name": safe_name,
        "uploaded_by": admin["username"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.epreuves.insert_one(doc)
    return {"message": "Épreuve ajoutée avec succès", "id": str(result.inserted_id)}


# ─── DELETE /api/epreuves/{id} ───────────────────────────────────────────────
@router.delete("/{epreuve_id}")
async def delete_epreuve(
    epreuve_id: str,
    admin: dict = Depends(get_admin_user)
):
    db = get_db()
    doc = await db.epreuves.find_one({"_id": ObjectId(epreuve_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Épreuve introuvable")

    # Supprimer le fichier physique
    file_path = os.path.join(UPLOAD_DIR, doc["file_name"])
    if os.path.exists(file_path):
        os.remove(file_path)

    await db.epreuves.delete_one({"_id": ObjectId(epreuve_id)})
    return {"message": "Épreuve supprimée avec succès"}
