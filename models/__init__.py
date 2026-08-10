"""
LEFAXEUR - Modèles Pydantic (Validation des données)
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from enum import Enum


class Role(str, Enum):
    admin = "admin"
    student = "student"


class DocumentType(str, Enum):
    cours = "cours"
    tp = "tp"
    evaluation = "evaluation"


class EvalType(str, Enum):
    interro = "interro"
    compo = "compo"
    examen = "examen"


# ─── Utilisateur ────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    username: EmailStr = Field(..., description="Identifiant unique (doit être un email)")
    password: str = Field(..., min_length=6)
    nom: str
    prenom: str
    email: EmailStr
    cycle: Optional[str] = None
    annee: Optional[int] = None
    role: Role = Role.student


class UserLogin(BaseModel):
    username: EmailStr
    password: str


class UserOut(BaseModel):
    username: str
    nom: str
    prenom: str
    email: str
    cycle: Optional[str] = None
    annee: Optional[int] = None
    role: str


# ─── Token JWT ──────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ─── Épreuves ───────────────────────────────────────────────────────────────
class EpreuveCreate(BaseModel):
    matiere: str
    cycle: str
    annee: int
    description: Optional[str] = None


class EpreuveOut(BaseModel):
    id: str
    matiere: str
    cycle: str
    annee: int
    description: Optional[str] = None
    file_url: str
    created_at: str


# ─── Informations/Annonces ───────────────────────────────────────────────────
class InfoCreate(BaseModel):
    titre: str
    contenu: str
    cycle: Optional[str] = "Général"
    annee_etude: Optional[int] = Field(None, ge=1, le=3)


class InfoOut(BaseModel):
    id: str
    titre: str
    contenu: str
    auteur: str
    cycle: Optional[str] = "Général"
    annee_etude: Optional[int] = None
    created_at: str
    file_url: Optional[str] = None
    file_type: Optional[str] = None  # 'image' | 'pdf'


# ─── Documents (Cours, TP, Évaluations) ─────────────────────────────────────
class DocumentOut(BaseModel):
    id: str
    titre: str
    type: str          # cours | tp | evaluation
    categorie_eval: Optional[str] = None  # interro | compo | examen
    matiere: str
    cycle: str
    annee: int
    file_url: str
    uploaded_by: str
    created_at: str

class SubjectCreate(BaseModel):
    cycle: str
    label: str
    matieres: List[str]


class SubjectOut(BaseModel):
    id: str
    cycle: str
    label: str
    matieres: List[str]
