"""
LEFAXEUR - Routes Administration
GET    /api/admin/stats              → Statistiques globales
GET    /api/admin/users              → Lister tous les utilisateurs
PATCH  /api/admin/users/{username}   → Modifier rôle / infos
DELETE /api/admin/users/{username}   → Supprimer un utilisateur
"""
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from database.db import get_db
from routes.auth import get_admin_user

router = APIRouter(prefix="/admin", tags=["Administration"])


def serialize_user(u: dict) -> dict:
    return {
        "id": str(u["_id"]),
        "username": u.get("username", ""),
        "nom": u.get("nom", ""),
        "prenom": u.get("prenom", ""),
        "email": u.get("email", ""),
        "cycle": u.get("cycle", "N/A"),
        "annee": u.get("annee", "N/A"),
        "role": u.get("role", "student"),
        "created_at": u.get("created_at", ""),
        "last_active": u.get("last_active"),
    }
    
    # Calculate online status (active in last 5 minutes)
    if u.get("last_active"):
        try:
            last_active = datetime.fromisoformat(u["last_active"])
            now = datetime.now(timezone.utc)
            if now - last_active < timedelta(minutes=5):
                base["is_online"] = True
            else:
                base["is_online"] = False
        except Exception:
            base["is_online"] = False
    else:
        base["is_online"] = False
        
    return base


# ─── GET /api/admin/stats ────────────────────────────────────────────────────
@router.get("/stats")
async def get_stats(admin: dict = Depends(get_admin_user)):
    db = get_db()
    total_users = await db.users.count_documents({})
    total_students = await db.users.count_documents({"role": "student"})
    total_admins = await db.users.count_documents({"role": "admin"})
    total_documents = await db.documents.count_documents({})
    total_infos = await db.infos.count_documents({})

    # Calculate online users
    five_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    total_online = await db.users.count_documents({"last_active": {"$gte": five_mins_ago}})

    # Répartition par cycle
    cycle_pipeline = [
        {"$match": {"role": "student"}},
        {"$group": {"_id": "$cycle", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    cycle_stats = []
    async for doc in db.users.aggregate(cycle_pipeline):
        cycle_stats.append({"cycle": doc["_id"] or "Non défini", "count": doc["count"]})

    # Dernières inscriptions (5 derniers)
    recent_users = []
    cursor = db.users.find({"role": "student"}).sort("_id", -1).limit(5)
    async for u in cursor:
        recent_users.append(serialize_user(u))

    return {
        "total_users": total_users,
        "total_students": total_students,
        "total_admins": total_admins,
        "total_documents": total_documents,
        "total_infos": total_infos,
        "total_online": total_online,
        "cycle_stats": cycle_stats,
        "recent_users": recent_users,
    }


# ─── GET /api/admin/users ────────────────────────────────────────────────────
@router.get("/users")
async def list_users(admin: dict = Depends(get_admin_user)):
    db = get_db()
    users = []
    async for u in db.users.find({}).sort("_id", -1):
        users.append(serialize_user(u))
    return users


# ─── PATCH /api/admin/users/{user_id}/role ───────────────────────────────────
@router.patch("/users/{user_id}/role")
async def update_user_role(user_id: str, role: str, admin: dict = Depends(get_admin_user)):
    if role not in ["admin", "student"]:
        raise HTTPException(status_code=400, detail="Rôle invalide. Valeurs acceptées : admin, student")
    db = get_db()
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": role}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return {"message": f"Rôle mis à jour : {role}"}


# ─── DELETE /api/admin/users/{user_id} ───────────────────────────────────────
@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(get_admin_user)):
    db = get_db()
    # Empêcher l'admin de se supprimer lui-même
    if str(admin["_id"]) == user_id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte")
    result = await db.users.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return {"message": "Utilisateur supprimé avec succès"}
