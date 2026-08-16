"""
LEFAXEUR - Routes Authentification
POST /api/auth/login
POST /api/auth/register
GET  /api/auth/me
"""
from fastapi import APIRouter, HTTPException, Depends, status, Body, Request
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timezone
from pymongo import ReturnDocument
from database.db import get_db
from models import UserCreate, UserLogin, UserOut, Token, UserProfileCompletion
from utils.helpers import hash_password, verify_password, create_access_token, decode_token
from utils.identity import student_registry_key
from utils.security import (
    ensure_persistent_login_allowed,
    record_persistent_failed_login,
    clear_persistent_failed_logins,
)

router = APIRouter(prefix="/auth", tags=["Authentification"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def profile_is_complete(user: dict) -> bool:
    return bool(user.get("sexe") and user.get("promotion") and user.get("authorized_student_id"))


async def claim_authorized_student(db, nom: str, prenom: str, sexe: str, promotion: str, username: str) -> dict:
    """Atomically reserve one official-register entry for one account."""
    key = student_registry_key(nom, prenom, sexe, promotion)
    student = await db.authorized_students.find_one_and_update(
        {**key, "$or": [
            {"claimed_by": {"$exists": False}}, {"claimed_by": None}, {"claimed_by": username}
        ]},
        {"$set": {"claimed_by": username, "claimed_at": datetime.now(timezone.utc).isoformat()}},
        return_document=ReturnDocument.AFTER,
    )
    if not student:
        raise HTTPException(status_code=403, detail="Student is not eligible or is already claimed")
    return student


# ─── Dépendance : Récupérer l'utilisateur courant depuis le token ────────────
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )
    db = get_db()
    user = await db.users.find_one({"username": payload.get("sub")})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    # A user can only have one active session.  Each successful login replaces
    # this value; a token from an older device is then rejected immediately.
    if not payload.get("sid") or user.get("active_session_id") != payload["sid"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée car ce compte a été utilisé sur un autre appareil",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé à l'administrateur")
    return current_user


# ─── POST /api/auth/login ────────────────────────────────────────────────────
@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    db = get_db()
    await ensure_persistent_login_allowed(db, credentials.username)
    user = await db.users.find_one({"username": credentials.username})

    if not user or not verify_password(credentials.password, user["password"]):
        await record_persistent_failed_login(db, credentials.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect"
        )
    # Administrators are managed separately from the student eligibility list.
    if user.get("role") != "admin" and not profile_is_complete(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "profile_completion_required",
                "message": "Complete your profile before accessing the site.",
                "nom": user.get("nom", ""),
                "prenom": user.get("prenom", ""),
                "email": user.get("email", credentials.username),
            },
        )
    await clear_persistent_failed_logins(db, credentials.username)
        
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": now, "last_active": now}}
    )

    token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    session_id = decode_token(token)["sid"]
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"active_session_id": session_id}}
    )
    user_out = UserOut(
        username=user["username"],
        nom=user["nom"],
        prenom=user["prenom"],
        email=user["email"],
        cycle=user.get("cycle"),
        annee=user.get("annee"),
        sexe=user.get("sexe"),
        promotion=user.get("promotion"),
        role=user["role"]
    )
    return Token(access_token=token, user=user_out)


# ─── POST /api/auth/register ─────────────────────────────────────────────────
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    db = get_db()

    # Vérifier si l'identifiant est déjà pris
    existing = await db.users.find_one({"username": user_data.username})
    if existing:
        raise HTTPException(status_code=400, detail="Cet identifiant est déjà utilisé")

    # Vérifier si l'email est déjà utilisé
    existing_email = await db.users.find_one({"email": user_data.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Cet email est déjà enregistré")

    authorized_student = await claim_authorized_student(
        db, user_data.nom, user_data.prenom, user_data.sexe, user_data.promotion, str(user_data.username)
    )
    new_user = {
        "username": user_data.username,
        "password": hash_password(user_data.password),
        "nom": user_data.nom,
        "prenom": user_data.prenom,
        "email": user_data.email,
        "cycle": user_data.cycle,
        "annee": user_data.annee,
        "sexe": user_data.sexe,
        "promotion": user_data.promotion,
        "authorized_student_id": str(authorized_student["_id"]),
        "role": "student",  # Les nouvelles inscriptions sont toujours 'student'
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        await db.users.insert_one(new_user)
    except Exception:
        await db.authorized_students.update_one(
            {"_id": authorized_student["_id"], "claimed_by": str(user_data.username)},
            {"$unset": {"claimed_by": "", "claimed_at": ""}},
        )
        raise
    return {"message": f"Compte créé avec succès pour {user_data.prenom} {user_data.nom}"}


# ─── GET /api/auth/me ────────────────────────────────────────────────────────
@router.post("/complete-profile")
async def complete_profile(data: UserProfileCompletion):
    """Validate legacy-account details against the official register."""
    db = get_db()
    user = await db.users.find_one({"username": data.username})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if profile_is_complete(user):
        raise HTTPException(status_code=400, detail="Profile is already complete")
    authorized_student = await claim_authorized_student(
        db, user["nom"], user["prenom"], data.sexe, data.promotion, str(data.username)
    )
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"sexe": data.sexe, "promotion": data.promotion,
                  "authorized_student_id": str(authorized_student["_id"])}},
    )
    return {"message": "Profile completed. Please log in again."}


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    return UserOut(
        username=current_user["username"],
        nom=current_user["nom"],
        prenom=current_user["prenom"],
        email=current_user["email"],
        cycle=current_user.get("cycle"),
        annee=current_user.get("annee"),
        sexe=current_user.get("sexe"),
        promotion=current_user.get("promotion"),
        role=current_user["role"]
    )

# ─── PATCH /api/auth/password ────────────────────────────────────────────────
@router.patch("/password")
async def update_password(
    old_password: str = Body(...),
    new_password: str = Body(...),
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    # Vérifier l'ancien mot de passe
    if not verify_password(old_password, current_user["password"]):
        raise HTTPException(status_code=400, detail="Ancien mot de passe incorrect")
        
    # Mettre à jour avec le nouveau
    hashed_new = hash_password(new_password)
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"password": hashed_new}}
    )
    
    return {"message": "Mot de passe mis à jour avec succès"}


# ─── POST /api/auth/heartbeat ────────────────────────────────────────────────
@router.post("/heartbeat")
async def heartbeat(current_user: dict = Depends(get_current_user)):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"last_active": now}}
    )
    return {"status": "ok"}
