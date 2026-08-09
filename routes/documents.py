"""
LEFAXEUR - Routes Documents (Cours, TP, Évaluations)
GET    /api/documents          → Lister (avec filtres)
POST   /api/documents          → Ajouter (Admin seulement)
DELETE /api/documents/{id}     → Supprimer (Admin seulement)
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional
import os, shutil

from database.db import get_db
from routes.auth import get_current_user, get_admin_user
from utils.email_sender import send_notification_email

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploads/documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def serialize_document(doc: dict) -> dict:
    """Convertit un document MongoDB en dict JSON-compatible.
    Gère deux types de documents :
      - Docs admin : ont un champ 'file_name' (fichier local uploadé)
      - Docs Drive : ont un champ 'file_url' (lien Google Drive direct)
    """
    # Construire l'URL du fichier selon le type de document
    if doc.get("file_name"):
        # Document uploadé via l'admin → fichier local sur le serveur
        file_url = f"/uploads/documents/{doc['file_name']}"
    else:
        # Document synchronisé depuis Google Drive → URL directe
        file_url = doc.get("file_url", "")

    return {
        "id": str(doc["_id"]),
        "titre": doc.get("titre", "Document sans titre"),
        "type": doc.get("type", "cours"),
        "categorie_eval": doc.get("categorie_eval"),
        "matiere": doc.get("matiere", ""),
        "cycle": doc.get("cycle", ""),
        "annee": doc.get("annee"),
        "file_url": file_url,
        "source": "drive" if not doc.get("file_name") else "admin",
        "uploaded_by": doc.get("uploaded_by", "Admin"),
        "created_at": doc.get("created_at", "")
    }


# ─── GET /api/documents ──────────────────────────────────────────────────────
@router.get("/")
async def list_documents(
    type: Optional[str] = Query(None),
    categorie_eval: Optional[str] = Query(None),
    cycle: Optional[str] = Query(None),
    matiere: Optional[str] = Query(None),
    annee: Optional[int] = Query(None),
    q: Optional[str] = Query(None),  # Recherche textuelle libre
    _: dict = Depends(get_current_user)  # Authentification requise
):
    db = get_db()
    query = {}
    if type:
        query["type"] = type
    if categorie_eval:
        query["categorie_eval"] = categorie_eval
    if cycle:
        query["cycle"] = cycle
    if matiere:
        query["matiere"] = {"$regex": matiere, "$options": "i"}
    if annee:
        query["annee"] = annee
    # Recherche textuelle sur titre ET matiere
    if q:
        query["$or"] = [
            {"titre": {"$regex": q, "$options": "i"}},
            {"matiere": {"$regex": q, "$options": "i"}},
        ]

    cursor = db.documents.find(query).sort("created_at", -1)
    results = []
    async for doc in cursor:
        try:
            results.append(serialize_document(doc))
        except Exception:
            # Ignorer les documents mal formés
            continue
    return results


# ─── POST /api/documents ─────────────────────────────────────────────────────
@router.post("/", status_code=201)
async def add_document(
    titre: str = Form(...),
    type: str = Form(...), # cours, tp, evaluation
    matiere: str = Form(...),
    cycle: str = Form(...),
    annee: int = Form(...),
    categorie_eval: Optional[str] = Form(None), # interro, compo, examen
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    admin: dict = Depends(get_admin_user)  # Admin seulement
):
    # Vérifier que c'est bien un PDF
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")

    db = get_db()

    # Sauvegarder le fichier
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = f"{type}_{cycle}_{matiere}_{annee}_{timestamp}.pdf".replace(" ", "_")
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    doc = {
        "titre": titre,
        "type": type,
        "categorie_eval": categorie_eval,
        "matiere": matiere,
        "cycle": cycle,
        "annee": annee,
        "file_name": safe_name,
        "uploaded_by": admin["username"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.documents.insert_one(doc)
    
    # Déclencher la notification par email
    sujet = f"Nouveau Document: {titre}"
    message = f"Un nouveau document de type '{type}' (Matière: {matiere}) a été publié pour le cycle {cycle}."
    if background_tasks:
        background_tasks.add_task(send_notification_email, cycle, sujet, message)
    
    return {"message": "Document ajouté avec succès", "id": str(result.inserted_id)}


# ─── PATCH /api/documents/{id} ───────────────────────────────────────────────
@router.patch("/{document_id}")
async def update_document(
    document_id: str,
    titre: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
    categorie_eval: Optional[str] = Form(None),
    matiere: Optional[str] = Form(None),
    cycle: Optional[str] = Form(None),
    annee: Optional[int] = Form(None),
    file: Optional[UploadFile] = File(None),
    admin: dict = Depends(get_admin_user)
):
    db = get_db()
    doc = await db.documents.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")

    update_data = {}
    if titre: update_data["titre"] = titre
    if type: update_data["type"] = type
    if categorie_eval is not None: update_data["categorie_eval"] = categorie_eval
    if matiere: update_data["matiere"] = matiere
    if cycle: update_data["cycle"] = cycle
    if annee: update_data["annee"] = annee

    if file and file.filename:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")
        
        # Supprimer l'ancien fichier
        old_file_path = os.path.join(UPLOAD_DIR, doc["file_name"])
        if os.path.exists(old_file_path):
            os.remove(old_file_path)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = f"{(type or doc['type'])}_{(cycle or doc['cycle'])}_{(matiere or doc['matiere'])}_{(annee or doc['annee'])}_{timestamp}.pdf".replace(" ", "_")
        file_path = os.path.join(UPLOAD_DIR, safe_name)

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        update_data["file_name"] = safe_name

    if update_data:
        await db.documents.update_one({"_id": ObjectId(document_id)}, {"$set": update_data})
        
    return {"message": "Document mis à jour avec succès"}


# ─── DELETE /api/documents/{id} ──────────────────────────────────────────────
@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    admin: dict = Depends(get_admin_user)
):
    db = get_db()
    doc = await db.documents.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")

    # Supprimer le fichier physique SEULEMENT si c'est un doc admin (file_name présent)
    if doc.get("file_name"):
        file_path = os.path.join(UPLOAD_DIR, doc["file_name"])
        if os.path.exists(file_path):
            os.remove(file_path)

    await db.documents.delete_one({"_id": ObjectId(document_id)})
    return {"message": "Document supprimé avec succès"}
