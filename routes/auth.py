"""
LEFAXEUR - Routes Authentification
POST /api/auth/login
POST /api/auth/register
GET  /api/auth/me
"""
from fastapi import APIRouter, HTTPException, Depends, status, Body
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timezone
from database.db import get_db
from models import UserCreate, UserLogin, UserOut, Token
from utils.helpers import hash_password, verify_password, create_access_token, decode_token

router = APIRouter(prefix="/auth", tags=["Authentification"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


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
    return user


async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé à l'administrateur")
    return current_user


# ─── POST /api/auth/login ────────────────────────────────────────────────────
@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    db = get_db()
    user = await db.users.find_one({"username": credentials.username})

    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect"
        )
        
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": now, "last_active": now}}
    )

    token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    user_out = UserOut(
        username=user["username"],
        nom=user["nom"],
        prenom=user["prenom"],
        email=user["email"],
        cycle=user.get("cycle"),
        annee=user.get("annee"),
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

    new_user = {
        "username": user_data.username,
        "password": hash_password(user_data.password),
        "nom": user_data.nom,
        "prenom": user_data.prenom,
        "email": user_data.email,
        "cycle": user_data.cycle,
        "annee": user_data.annee,
        "role": "student",  # Les nouvelles inscriptions sont toujours 'student'
    }

    await db.users.insert_one(new_user)
    return {"message": f"Compte créé avec succès pour {user_data.prenom} {user_data.nom}"}


# ─── GET /api/auth/me ────────────────────────────────────────────────────────
@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    return UserOut(
        username=current_user["username"],
        nom=current_user["nom"],
        prenom=current_user["prenom"],
        email=current_user["email"],
        cycle=current_user.get("cycle"),
        annee=current_user.get("annee"),
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
