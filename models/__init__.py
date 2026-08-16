"""
LEFAXEUR - Modèles Pydantic (Validation des données)
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Literal
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
    password: str = Field(..., min_length=15, max_length=72)
    nom: str
    prenom: str
    email: EmailStr
    cycle: Optional[str] = None
    annee: Optional[int] = None
    sexe: Literal["M", "F"]
    promotion: str = Field(..., min_length=3, max_length=80)
    role: Role = Role.student

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        common_passwords = {"Password123456", "Admin123456789", "Azerty123456789", "123456789012345"}
        if value in common_passwords:
            raise ValueError("Ce mot de passe est trop courant")
        if not (any(c.islower() for c in value) and any(c.isupper() for c in value)
                and any(c.isdigit() for c in value)):
            raise ValueError("Le mot de passe doit contenir une minuscule, une majuscule et un chiffre")
        return value


class UserLogin(BaseModel):
    username: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class UserProfileCompletion(BaseModel):
    username: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    sexe: Literal["M", "F"]
    promotion: str = Field(..., min_length=3, max_length=80)


class UserOut(BaseModel):
    username: str
    nom: str
    prenom: str
    email: str
    cycle: Optional[str] = None
    annee: Optional[int] = None
    sexe: Optional[str] = None
    promotion: Optional[str] = None
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
