"""
LEFAXEUR - Routes Suivi des Volumes Horaires
GET    /api/heures/{annee}           → Heures cumulées + progression globale
POST   /api/heures/semaine           → Admin enregistre les heures d'une semaine (global)
GET    /api/heures/semaines/{annee}  → Admin liste les entrées hebdomadaires
DELETE /api/heures/semaine/{id}      → Admin supprime une entrée de semaine
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from bson import ObjectId
from datetime import datetime, timezone

from database.db import get_db
from routes.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/heures", tags=["Volumes Horaires"])

# ─── Totaux de référence (PDF EAMAC 2024-2025) ───────────────────────────────
TOTAUX_ANNEE = {
    1: 1047,   # SEI 1ère année
    2: 1047,   # SEI 2ème année
}

# Répartition par catégorie pour affichage (pourcentage du total)
CATEGORIES_SEI1 = [
    {"label": "Matières Principales Professionnelles", "h": 401, "icon": "⚡"},
    {"label": "Matières Principales Générales (Anglais)", "h": 72,  "icon": "🌍"},
    {"label": "Matières Secondaires Professionnelles", "h": 540, "icon": "🔧"},
    {"label": "Matières Secondaires Générales (EPS)", "h": 34,  "icon": "🏃"},
]
CATEGORIES_SEI2 = [
    {"label": "Matières Principales Professionnelles", "h": 354, "icon": "📡"},
    {"label": "Groupe Radionavigation",                "h": 45,  "icon": "🛫"},
    {"label": "Groupe Radar",                          "h": 55,  "icon": "📶"},
    {"label": "Groupe Réseaux",                        "h": 65,  "icon": "🌐"},
    {"label": "Matières Principales Générales (Anglais)", "h": 60, "icon": "🌍"},
    {"label": "Matières Secondaires Professionnelles", "h": 440, "icon": "🔧"},
    {"label": "Matières Secondaires Générales",        "h": 63,  "icon": "📋"},
]

CATEGORIES = {1: CATEGORIES_SEI1, 2: CATEGORIES_SEI2}


# ─── GET /api/heures/{annee} ──────────────────────────────────────────────────
@router.get("/{annee}")
async def get_heures(
    annee: int,
    _: dict = Depends(get_current_user)
):
    """Retourne la progression globale des heures pour une année (1 ou 2)."""
    if annee not in TOTAUX_ANNEE:
        raise HTTPException(status_code=404, detail="Année non reconnue (1 ou 2)")

    db = get_db()
    total_prevu = TOTAUX_ANNEE[annee]

    # Sommer toutes les heures enregistrées
    heures_effectuees = 0
    semaines = []
    cursor = db.heures_semaines.find({"annee": annee}).sort("semaine", -1)
    async for doc in cursor:
        h = doc.get("heures_totales", 0)
        heures_effectuees += h
        semaines.append({
            "id": str(doc["_id"]),
            "semaine": doc["semaine"],
            "heures_totales": h,
            "enregistre_par": doc.get("enregistre_par", ""),
            "created_at": doc.get("created_at", "")
        })

    heures_restantes = max(0, total_prevu - heures_effectuees)
    pct = round(min(100, (heures_effectuees / total_prevu) * 100))

    # Estimation de la progression par catégorie
    categories = []
    for cat in CATEGORIES.get(annee, []):
        cat_pct = round(min(100, (heures_effectuees / total_prevu) * 100)) if total_prevu > 0 else 0
        cat_effectuees = round(cat["h"] * pct / 100)
        categories.append({
            "label": cat["label"],
            "icon": cat["icon"],
            "total_h": cat["h"],
            "effectuees_h": cat_effectuees,
            "restantes_h": max(0, cat["h"] - cat_effectuees),
            "pct": cat_pct
        })

    return {
        "annee": annee,
        "total_prevu_h": total_prevu,
        "heures_effectuees": heures_effectuees,
        "heures_restantes": heures_restantes,
        "progression_pct": pct,
        "categories": categories,
        "semaines": semaines
    }


# ─── POST /api/heures/semaine ─────────────────────────────────────────────────
@router.post("/semaine", status_code=201)
async def sauvegarder_semaine(
    annee: int = Body(...),
    semaine: str = Body(...),          # ex: "2026-W32"
    heures_totales: float = Body(...), # heures effectuées cette semaine
    commentaire: str = Body(""),
    admin: dict = Depends(get_admin_user)
):
    """Admin enregistre les heures globales effectuées durant une semaine."""
    if annee not in TOTAUX_ANNEE:
        raise HTTPException(status_code=400, detail="Année non reconnue (1 ou 2)")

    db = get_db()

    # Vérifier doublon
    existing = await db.heures_semaines.find_one({"annee": annee, "semaine": semaine})
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Les heures pour la semaine {semaine} (Année {annee}) ont déjà été enregistrées."
        )

    doc = {
        "annee": annee,
        "semaine": semaine,
        "heures_totales": heures_totales,
        "commentaire": commentaire,
        "enregistre_par": admin.get("username", "admin"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.heures_semaines.insert_one(doc)
    return {"message": f"Semaine {semaine} enregistrée ({heures_totales}h)", "id": str(result.inserted_id)}


# ─── GET /api/heures/semaines/{annee} ────────────────────────────────────────
@router.get("/semaines/{annee}")
async def list_semaines(
    annee: int,
    admin: dict = Depends(get_admin_user)
):
    """Admin: liste toutes les entrées de semaines pour une année."""
    if annee not in TOTAUX_ANNEE:
        raise HTTPException(status_code=404, detail="Année non reconnue")

    db = get_db()
    cursor = db.heures_semaines.find({"annee": annee}).sort("semaine", -1)
    results = []
    async for doc in cursor:
        results.append({
            "id": str(doc["_id"]),
            "annee": doc["annee"],
            "semaine": doc["semaine"],
            "heures_totales": doc.get("heures_totales", 0),
            "commentaire": doc.get("commentaire", ""),
            "enregistre_par": doc.get("enregistre_par", ""),
            "created_at": doc.get("created_at", "")
        })
    return results


# ─── DELETE /api/heures/semaine/{id} ─────────────────────────────────────────
@router.delete("/semaine/{entry_id}")
async def delete_semaine(
    entry_id: str,
    admin: dict = Depends(get_admin_user)
):
    """Admin: supprime une entrée de semaine."""
    db = get_db()
    doc = await db.heures_semaines.find_one({"_id": ObjectId(entry_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Entrée introuvable")

    await db.heures_semaines.delete_one({"_id": ObjectId(entry_id)})
    return {"message": "Entrée supprimée avec succès"}
