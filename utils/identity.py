"""Normalization helpers for matching students against the official register."""
import re
import unicodedata


def normalize_identity(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value).strip().upper()


def normalize_promotion(value: str) -> str:
    return normalize_identity(value)


def student_registry_key(nom: str, prenom: str, sexe: str, promotion: str) -> dict:
    return {
        "nom_normalized": normalize_identity(nom),
        "prenom_normalized": normalize_identity(prenom),
        "sexe": (sexe or "").strip().upper(),
        "promotion_normalized": normalize_promotion(promotion),
    }
