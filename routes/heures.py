"""
LEFAXEUR - Routes Suivi des Volumes Horaires
GET    /api/heures/{cycle}          → Heures cumulées par matière pour un cycle
POST   /api/heures/semaine          → Admin enregistre les heures d'une semaine
GET    /api/heures/semaines/{cycle} → Admin liste les entrées hebdomadaires
DELETE /api/heures/semaine/{id}     → Admin supprime une entrée de semaine
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional, List
import json

from database.db import get_db
from routes.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/heures", tags=["Volumes Horaires"])


# ─── Données de référence des volumes horaires ────────────────────────────────

VOLUMES_SEI1 = [
    # Matières Principales Professionnelles
    {"matiere": "Électricité générale", "categorie": "Principales Prof.", "total_h": 30},
    {"matiere": "Circuits électriques", "categorie": "Principales Prof.", "total_h": 50},
    {"matiere": "Électronique fondamentale", "categorie": "Principales Prof.", "total_h": 100},
    {"matiere": "Électronique numérique", "categorie": "Principales Prof.", "total_h": 100},
    {"matiere": "Algorithmique et Programmation C", "categorie": "Principales Prof.", "total_h": 49},
    {"matiere": "Technologies, Matières et Composants Électroniques", "categorie": "Principales Prof.", "total_h": 40},
    {"matiere": "Appareils de mesure et outillage pour électronicien", "categorie": "Principales Prof.", "total_h": 32},
    # Matières Principales Générales
    {"matiere": "Anglais général", "categorie": "Principales Gén.", "total_h": 40},
    {"matiere": "Anglais technique et professionnel", "categorie": "Principales Gén.", "total_h": 32},
    # Matières Secondaires Professionnelles
    {"matiere": "Amplificateur opérationnel", "categorie": "Secondaires Prof.", "total_h": 32},
    {"matiere": "Machines électriques", "categorie": "Secondaires Prof.", "total_h": 32},
    {"matiere": "Électronique de puissance", "categorie": "Secondaires Prof.", "total_h": 32},
    {"matiere": "Automatique", "categorie": "Secondaires Prof.", "total_h": 32},
    {"matiere": "Architecture et configuration PC", "categorie": "Secondaires Prof.", "total_h": 30},
    {"matiere": "Environnement bureautique", "categorie": "Secondaires Prof.", "total_h": 25},
    {"matiere": "Organisations et Normes", "categorie": "Secondaires Prof.", "total_h": 20},
    {"matiere": "Circulation aérienne", "categorie": "Secondaires Prof.", "total_h": 20},
    {"matiere": "Aérotechnique", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Météorologie", "categorie": "Secondaires Prof.", "total_h": 20},
    {"matiere": "Sécurité incendie", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Communications et Réseaux ATM", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Navigation CNS/ATM", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Surveillance", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Secourisme", "categorie": "Secondaires Prof.", "total_h": 20},
    {"matiere": "Introduction aux Réseaux", "categorie": "Secondaires Prof.", "total_h": 20},
    {"matiere": "Transmission de données", "categorie": "Secondaires Prof.", "total_h": 32},
    {"matiere": "Les réseaux nationaux", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Les réseaux internationaux", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Les réseaux mondiaux", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Les protocoles", "categorie": "Secondaires Prof.", "total_h": 20},
    {"matiere": "Commutateur de messages", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Systèmes de gestion de l'information aéronautique", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Traitement de données de surveillance", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Appareils de mesure et outillage pour électricien/électrotechnicien", "categorie": "Secondaires Prof.", "total_h": 20},
    {"matiere": "Transport d'énergie électrique", "categorie": "Secondaires Prof.", "total_h": 15},
    {"matiere": "Transport de données", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Systèmes de production et de gestion énergie", "categorie": "Secondaires Prof.", "total_h": 30},
    {"matiere": "Balisage", "categorie": "Secondaires Prof.", "total_h": 20},
    # Matières Secondaires Générales
    {"matiere": "Éducation physique", "categorie": "Secondaires Gén.", "total_h": 34},
    {"matiere": "Assiduité", "categorie": "Secondaires Gén.", "total_h": 0},
]

VOLUMES_SEI2 = [
    # Matières Principales Professionnelles
    {"matiere": "Microprocesseur-Microcontrôleur", "categorie": "Principales Prof.", "total_h": 62},
    {"matiere": "Émission/Réception", "categorie": "Principales Prof.", "total_h": 65},
    {"matiere": "Lignes et hyperfréquences", "categorie": "Principales Prof.", "total_h": 45},
    {"matiere": "Projet Fin d'études", "categorie": "Principales Prof.", "total_h": 64},
    # Groupe Radionavigation
    {"matiere": "VOR", "categorie": "Radionavigation", "total_h": 15},
    {"matiere": "ILS", "categorie": "Radionavigation", "total_h": 20},
    {"matiere": "DME", "categorie": "Radionavigation", "total_h": 10},
    # Groupe Radar
    {"matiere": "Radar du contrôle aérien (Primaire, secondaire)", "categorie": "Radar", "total_h": 30},
    {"matiere": "Transmission de données radar", "categorie": "Radar", "total_h": 10},
    {"matiere": "Radar météo (primaire et profileur de vent)", "categorie": "Radar", "total_h": 15},
    # Groupe Réseaux
    {"matiere": "Routeur CISCO et sécurité", "categorie": "Réseaux", "total_h": 30},
    {"matiere": "Pare-feu (Fortigate...)", "categorie": "Réseaux", "total_h": 20},
    {"matiere": "VPN et ressources Internet", "categorie": "Réseaux", "total_h": 15},
    # Matières Principales Générales
    {"matiere": "Anglais général", "categorie": "Principales Gén.", "total_h": 30},
    {"matiere": "Anglais technique et professionnel", "categorie": "Principales Gén.", "total_h": 30},
    # Matières Secondaires Professionnelles
    {"matiere": "Système d'exploitation (Linux-Windows)", "categorie": "Secondaires Prof.", "total_h": 30},
    {"matiere": "Bases de données", "categorie": "Secondaires Prof.", "total_h": 30},
    {"matiere": "Simulateur de vol", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Maintenance (concept, instructions et GMAO)", "categorie": "Secondaires Prof.", "total_h": 20},
    {"matiere": "Facteurs humains", "categorie": "Secondaires Prof.", "total_h": 20},
    {"matiere": "Poste et milieu de travail", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Protection de l'environnement", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Moyens et installations", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Sécurité (concept, gestion, politique, règlements)", "categorie": "Secondaires Prof.", "total_h": 15},
    {"matiere": "Gestion des risques", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Sécurité des systèmes informatiques", "categorie": "Secondaires Prof.", "total_h": 20},
    {"matiere": "Cybersécurité", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Gestion de chantier (conduite, attitude, prévention)", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Antennes", "categorie": "Secondaires Prof.", "total_h": 30},
    {"matiere": "Propagation en espace libre", "categorie": "Secondaires Prof.", "total_h": 20},
    {"matiere": "Équipements VHF", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Téléphonie", "categorie": "Secondaires Prof.", "total_h": 30},
    {"matiere": "Systèmes de chaînes de radiotéléphonie (VCCS)", "categorie": "Secondaires Prof.", "total_h": 20},
    {"matiere": "Multiplexeurs et Commutateurs", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Équipements VSAT et Énergie", "categorie": "Secondaires Prof.", "total_h": 20},
    {"matiere": "Techniques satellitaires", "categorie": "Secondaires Prof.", "total_h": 25},
    {"matiere": "Faisceaux Hertziens", "categorie": "Secondaires Prof.", "total_h": 24},
    {"matiere": "Enregistreurs (ASSMANN MDR2000, ASSMANN2015, MARATHON EVOLUTION)", "categorie": "Secondaires Prof.", "total_h": 15},
    {"matiere": "GNSS (GPS, GLONASS, GALILEO...)", "categorie": "Secondaires Prof.", "total_h": 20},
    {"matiere": "ADS (Concept général, ADS-B, ADS-C)", "categorie": "Secondaires Prof.", "total_h": 15},
    {"matiere": "Multilatération", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Stations synoptiques-SAOMA", "categorie": "Secondaires Prof.", "total_h": 25},
    {"matiere": "SAAPI", "categorie": "Secondaires Prof.", "total_h": 10},
    {"matiere": "Radiosondage météorologique", "categorie": "Secondaires Prof.", "total_h": 30},
    {"matiere": "Stage immersion", "categorie": "Secondaires Prof.", "total_h": 4},
    # Matières Secondaires Générales
    {"matiere": "Règles-Procédures-Législation", "categorie": "Secondaires Gén.", "total_h": 15},
    {"matiere": "Rédaction administrative", "categorie": "Secondaires Gén.", "total_h": 20},
    {"matiere": "Assiduité", "categorie": "Secondaires Gén.", "total_h": 0},
    {"matiere": "EPS", "categorie": "Secondaires Gén.", "total_h": 28},
]


def get_volumes_for_cycle(annee: int):
    """Retourne les volumes horaires selon l'année (1=SEI1, 2=SEI2)."""
    if annee == 1:
        return VOLUMES_SEI1
    elif annee == 2:
        return VOLUMES_SEI2
    return []


# ─── GET /api/heures/{cycle}/{annee} ─────────────────────────────────────────
@router.get("/{annee}")
async def get_heures(
    annee: int,
    _: dict = Depends(get_current_user)
):
    """Retourne les volumes horaires avec les heures cumulées pour un cycle/année."""
    db = get_db()
    volumes = get_volumes_for_cycle(annee)
    
    if not volumes:
        raise HTTPException(status_code=404, detail="Cycle non trouvé")

    # Récupérer les heures cumulées depuis MongoDB
    cumul_cursor = db.heures_semaines.find({"annee": annee})
    cumul = {}  # {matiere: heures_effectuees}
    
    async for entry in cumul_cursor:
        for mat_entry in entry.get("matieres", []):
            mat = mat_entry["matiere"]
            h = mat_entry.get("heures", 0)
            cumul[mat] = cumul.get(mat, 0) + h

    # Construire la réponse
    result = []
    for vol in volumes:
        mat = vol["matiere"]
        total = vol["total_h"]
        effectuees = cumul.get(mat, 0)
        restantes = max(0, total - effectuees)
        pct = round((effectuees / total * 100) if total > 0 else 0)
        
        result.append({
            "matiere": mat,
            "categorie": vol["categorie"],
            "total_h": total,
            "effectuees_h": effectuees,
            "restantes_h": restantes,
            "progression_pct": pct
        })

    return result


# ─── POST /api/heures/semaine ─────────────────────────────────────────────────
@router.post("/semaine", status_code=201)
async def sauvegarder_semaine(
    annee: int = Body(...),
    semaine: str = Body(...),   # ex: "2026-W32"
    matieres: list = Body(...), # [{matiere: str, heures: float}]
    admin: dict = Depends(get_admin_user)
):
    """Admin enregistre les heures effectuées durant une semaine."""
    db = get_db()
    
    # Vérifier s'il y a déjà une entrée pour cette semaine/annee
    existing = await db.heures_semaines.find_one({"annee": annee, "semaine": semaine})
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Les heures pour la semaine {semaine} (Année {annee}) ont déjà été enregistrées. Supprimez d'abord l'entrée existante."
        )

    doc = {
        "annee": annee,
        "semaine": semaine,
        "matieres": matieres,
        "enregistre_par": admin["username"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.heures_semaines.insert_one(doc)
    return {"message": f"Heures de la semaine {semaine} enregistrées avec succès", "id": str(result.inserted_id)}


# ─── GET /api/heures/semaines/{annee} ────────────────────────────────────────
@router.get("/semaines/{annee}")
async def list_semaines(
    annee: int,
    admin: dict = Depends(get_admin_user)
):
    """Admin: liste toutes les entrées de semaines pour un cycle/année."""
    db = get_db()
    cursor = db.heures_semaines.find({"annee": annee}).sort("semaine", -1)
    results = []
    async for doc in cursor:
        results.append({
            "id": str(doc["_id"]),
            "annee": doc["annee"],
            "semaine": doc["semaine"],
            "nb_matieres": len(doc.get("matieres", [])),
            "enregistre_par": doc.get("enregistre_par", ""),
            "created_at": doc.get("created_at", ""),
            "matieres": doc.get("matieres", [])
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


# ─── GET /api/heures/volumes/{annee} ─────────────────────────────────────────
@router.get("/volumes/{annee}")
async def get_volumes(
    annee: int,
    _: dict = Depends(get_current_user)
):
    """Retourne les volumes horaires de référence (sans les heures effectuées)."""
    volumes = get_volumes_for_cycle(annee)
    if not volumes:
        raise HTTPException(status_code=404, detail="Cycle non trouvé")
    return volumes
