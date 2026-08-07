"""
LEFAXEUR - Routes Informations / Annonces
GET    /api/infos      → Lister toutes les annonces
POST   /api/infos      → Publier une annonce avec fichier optionnel (Admin)
DELETE /api/infos/{id} → Supprimer une annonce (Admin)
"""
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form, BackgroundTasks
from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional
import os, shutil

from database.db import get_db
from routes.auth import get_current_user, get_admin_user
from utils.email_sender import send_notification_email

router = APIRouter(prefix="/infos", tags=["Informations"])

UPLOAD_DIR_INFOS = "uploads/infos"
os.makedirs(UPLOAD_DIR_INFOS, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


def serialize_info(doc: dict) -> dict:
    result = {
        "id": str(doc["_id"]),
        "titre": doc["titre"],
        "contenu": doc["contenu"],
        "auteur": doc.get("auteur", "LEFAXEUR"),
        "cycle": doc.get("cycle", "Général"),
        "created_at": doc.get("created_at", ""),
        "file_url": doc.get("file_url"),
        "file_type": doc.get("file_type"),
    }
    return result


# ─── GET /api/infos ──────────────────────────────────────────────────────────
@router.get("/")
async def list_infos(
    cycle: Optional[str] = Query(None),
    _: dict = Depends(get_current_user)
):
    db = get_db()

    query = {}
    if cycle:
        query["cycle"] = {"$in": ["Général", cycle]}

    cursor = db.infos.find(query).sort("created_at", -1)
    results = []
    async for doc in cursor:
        results.append(serialize_info(doc))
    return results


# ─── POST /api/infos (multipart) ─────────────────────────────────────────────
@router.post("/", status_code=201)
async def add_info(
    titre: str = Form(...),
    contenu: str = Form(...),
    background_tasks: BackgroundTasks = None,
    cycle: str = Form("Général"),
    file: Optional[UploadFile] = File(None),
    admin: dict = Depends(get_admin_user)
):
    db = get_db()

    file_url = None
    file_type = None

    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Type de fichier non supporté. Acceptés : PDF, JPG, PNG"
            )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = f"info_{timestamp}{ext}".replace(" ", "_")
        file_path = os.path.join(UPLOAD_DIR_INFOS, safe_name)

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        file_url = f"/uploads/infos/{safe_name}"
        file_type = "pdf" if ext == ".pdf" else "image"

    doc = {
        "titre": titre,
        "contenu": contenu,
        "auteur": f"{admin['prenom']} {admin['nom']}",
        "cycle": cycle,
        "file_url": file_url,
        "file_type": file_type,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.infos.insert_one(doc)
    
    # Déclencher la notification par email
    sujet = f"Nouvelle Information: {titre}"
    message = f"Une nouvelle annonce a été publiée :<br><b>{titre}</b><br><br>Connectez-vous pour lire les détails."
    if background_tasks:
        background_tasks.add_task(send_notification_email, cycle, sujet, message)

    return {"message": "Information publiée avec succès", "id": str(result.inserted_id)}


# ─── PATCH /api/infos/{id} ───────────────────────────────────────────────────
@router.patch("/{info_id}")
async def update_info(
    info_id: str,
    titre: Optional[str] = Form(None),
    contenu: Optional[str] = Form(None),
    cycle: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    admin: dict = Depends(get_admin_user)
):
    db = get_db()
    doc = await db.infos.find_one({"_id": ObjectId(info_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Annonce introuvable")

    update_data = {}
    if titre: update_data["titre"] = titre
    if contenu: update_data["contenu"] = contenu
    if cycle: update_data["cycle"] = cycle

    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Type de fichier non supporté. Acceptés : PDF, JPG, PNG")
        
        # Supprimer l'ancien fichier
        if doc.get("file_url"):
            old_file_path = "." + doc["file_url"]
            if os.path.exists(old_file_path):
                os.remove(old_file_path)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = f"info_{timestamp}{ext}".replace(" ", "_")
        file_path = os.path.join(UPLOAD_DIR_INFOS, safe_name)

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        update_data["file_url"] = f"/uploads/infos/{safe_name}"
        update_data["file_type"] = "pdf" if ext == ".pdf" else "image"

    if update_data:
        await db.infos.update_one({"_id": ObjectId(info_id)}, {"$set": update_data})
        
    return {"message": "Annonce mise à jour avec succès"}


# ─── DELETE /api/infos/{id} ──────────────────────────────────────────────────
@router.delete("/{info_id}")
async def delete_info(info_id: str, admin: dict = Depends(get_admin_user)):
    db = get_db()
    doc = await db.infos.find_one({"_id": ObjectId(info_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Annonce introuvable")

    # Supprimer le fichier physique s'il existe
    if doc.get("file_url"):
        file_path = "." + doc["file_url"]
        if os.path.exists(file_path):
            os.remove(file_path)

    await db.infos.delete_one({"_id": ObjectId(info_id)})
    return {"message": "Annonce supprimée avec succès"}
