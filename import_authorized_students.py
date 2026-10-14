"""Import an official student spreadsheet into MongoDB.

Usage:
    python import_authorized_students.py CHEMIN_DU_FICHIER.xlsx "EAC SEI 2026" "EAC SEI 2025"

The spreadsheet must contain the columns ``Nom``, ``Prénom`` and ``Sexe``.
When an old promotion prefix is explicitly supplied, matching students are
removed only from that promotion. Other cycles and promotions are untouched.
"""
import os
import re
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from openpyxl import load_workbook
from pymongo import MongoClient, UpdateOne

from utils.identity import normalize_identity, student_registry_key


REQUIRED_COLUMNS = {"nom", "prenom", "sexe"}


def normalized_header(value: object) -> str:
    return normalize_identity(str(value or "")).lower()


def main(path: str, promotion: str, old_promotion_prefix: str | None = None) -> None:
    if not os.path.isfile(path):
        raise SystemExit("Fichier Excel introuvable.")
    promotion = promotion.strip()
    if not promotion:
        raise SystemExit("La promotion ne peut pas être vide.")

    load_dotenv()
    mongo_url = os.getenv("MONGODB_URL")
    db_name = os.getenv("DB_NAME", "lefaxeur_db")
    if not mongo_url:
        raise SystemExit("MONGODB_URL doit être défini dans .env.")

    sheet = load_workbook(path, read_only=True, data_only=True).active
    rows = sheet.iter_rows(values_only=True)
    try:
        headers = next(rows)
    except StopIteration:
        raise SystemExit("Le fichier Excel est vide.")
    column_indexes = {
        normalized_header(header): index
        for index, header in enumerate(headers)
        if header is not None
    }
    missing = REQUIRED_COLUMNS - set(column_indexes)
    if missing:
        raise SystemExit(f"Colonnes manquantes : {', '.join(sorted(missing))}.")

    operations = []
    identities = []
    seen = set()
    for row in rows:
        nom = row[column_indexes["nom"]] if len(row) > column_indexes["nom"] else None
        prenom = row[column_indexes["prenom"]] if len(row) > column_indexes["prenom"] else None
        sexe = row[column_indexes["sexe"]] if len(row) > column_indexes["sexe"] else None
        if not all((nom, prenom, sexe)):
            continue
        key = student_registry_key(str(nom), str(prenom), str(sexe), promotion)
        if key["sexe"] not in {"M", "F"}:
            raise SystemExit(f"Sexe invalide dans le fichier pour {nom} {prenom}.")
        identity = (key["nom_normalized"], key["prenom_normalized"], key["sexe"])
        if identity in seen:
            continue
        seen.add(identity)
        identities.append(identity)
        operations.append(UpdateOne(
            key,
            {"$setOnInsert": {
                **key,
                "nom": str(nom).strip(),
                "prenom": str(prenom).strip(),
                "promotion": promotion,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        ))

    client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
    collection = client[db_name].authorized_students
    collection.create_index([
        ("nom_normalized", 1), ("prenom_normalized", 1), ("sexe", 1), ("promotion_normalized", 1)
    ], unique=True)
    result = collection.bulk_write(operations, ordered=False) if operations else None

    old_entries_removed = 0
    if old_promotion_prefix:
        old_promotion_prefix = normalize_identity(old_promotion_prefix)
        old_promotion_pattern = f"^{re.escape(old_promotion_prefix)}(?: |$)"
        for nom_normalized, prenom_normalized, sexe in identities:
            deletion = collection.delete_many({
                "nom_normalized": nom_normalized,
                "prenom_normalized": prenom_normalized,
                "sexe": sexe,
                "promotion_normalized": {"$regex": old_promotion_pattern},
            })
            old_entries_removed += deletion.deleted_count
    print(
        f"Registre traité : {len(operations)} élèves; "
        f"{result.upserted_count if result else 0} ajoutés; "
        f"{old_entries_removed} anciennes entrées supprimées."
    )
    client.close()


if __name__ == "__main__":
    if len(sys.argv) not in {3, 4}:
        raise SystemExit(
            "Usage : python import_authorized_students.py CHEMIN_DU_FICHIER.xlsx PROMOTION [ANCIENNE_PROMOTION]"
        )
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None)
