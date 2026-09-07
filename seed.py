"""
LEFAXEUR - Script d'initialisation de la base de données
Lance ce script UNE SEULE FOIS pour créer les données de base :
- Tous les cycles et matières (hors Assiduité et EPS)

Usage : python seed.py
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from passlib.context import CryptContext
import os

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "lefaxeur_db")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


SUBJECTS_DATA = [
    {
        "cycle": "IEAMAC-NA",
        "label": "Cycle Ingénieur (IEAMAC/NA)",
        "matieres": ["Navigation aérienne", "Aérodynamique", "Mécanique du vol", "Droit aérien", "Réglementation technique", "Météorologie", "Anglais technique", "Gestion de la sécurité"]
    },
    {
        "cycle": "EAC-NA",
        "label": "Cycle Exploitation Aéronautique Civile (EAC/NA)",
        "matieres": ["Exploitation BDP/SIA", "Réglementation du transport aérien", "Opérations aériennes", "Cartographie aéronautique", "Navigation aérienne", "Météorologie aéronautique", "Anglais général"]
    },
    {
        "cycle": "T-NA",
        "label": "Cycle Technicien (T/NA)",
        "matieres": ["Infrastructure aéroportuaire et balisage", "Bureau de Piste", "Service de l'information aéronautique", "Service mobile aéronautique", "Secourisme", "Anglais"]
    },
    {
        "cycle": "CCA",
        "label": "Contrôleur Circulation Aérienne (CCA)",
        "matieres": ["RCA : Contrôle d'aérodrome", "RCA : Contrôle d'approche", "RCA : Contrôle en route", "PANS/OPS", "Exploitation radar", "Météo Générale", "Anglais Phraséologie", "Secourisme"]
    },
    {
        "cycle": "IEAMAC-SEI",
        "label": "Cycle Ingénieur (IEAMAC/SEI)",
        "matieres": ["Circuits Electriques", "Electronique Numérique", "Microprocesseurs", "Transmissions numériques", "Radionavigation", "Radar", "Télécommunications par satellites", "Réseaux informatiques"]
    },
    {
        "cycle": "EAC-SEI",
        "label": "Cycle Exploitation Aéronautique Civile (EAC/SEI)",
        "matieres": ["Réseaux de télécommunications aéronautiques (ATN)", "Maintenance", "Equipements MTO satellitaires", "Antennes - Propagation", "Emission / Réception", "Administration réseau", "CNS/ATM"]
    },
    {
        "cycle": "IEAMAC-M",
        "label": "Cycle Ingénieur (IEAMAC/M)",
        "matieres": ["Météorologie générale", "Météorologie aéronautique", "Météorologie tropicale", "Thermodynamique", "Mécanique des fluides", "Physique", "Mathématiques", "Prévision météorologique"]
    },
    {
        "cycle": "EAC-M",
        "label": "Cycle Exploitation Aéronautique Civile (EAC/M)",
        "matieres": ["Assistance météorologique à la NA", "Observation météorologique", "Instruments météorologiques", "Climatologie", "Codes OPMET", "Transmission des données météorologiques"]
    },
    {
        "cycle": "T-M",
        "label": "Cycle Technicien (T/M)",
        "matieres": ["Observation au sol", "Lecture des instruments", "Transmission MTO", "Anglais technique", "Informatique de base", "Secourisme"]
    }
]


USERS_DATA = [
    {
        "username": "admin@lefaxeur.aero",
        "password": pwd_context.hash("admin2026"),
        "nom": "Administrateur",
        "prenom": "LEFAXEUR",
        "email": "admin@lefaxeur.aero",
        "cycle": None,
        "annee": None,
        "role": "admin"
    },
    {
        "username": "user@lefaxeur.aero",
        "password": pwd_context.hash("user2026"),
        "nom": "Étudiant",
        "prenom": "Test",
        "email": "user@lefaxeur.aero",
        "cycle": "IEAMAC-NA",
        "annee": 1,
        "role": "student"
    }
]


async def seed():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]

    print("[START] Démarrage du seeding LEFAXEUR...")

    # ─── Utilisateurs ───────────────────────────────────────────────────────
    for user in USERS_DATA:
        existing = await db.users.find_one({"username": user["username"]})
        if existing:
            print(f"  [WARN]  Utilisateur '{user['username']}' existe déjà, ignoré.")
        else:
            await db.users.insert_one(user)
            print(f"  [OK] Utilisateur '{user['username']}' créé avec succès.")

    # ─── Cycles et Matières ─────────────────────────────────────────────────
    for subject in SUBJECTS_DATA:
        existing = await db.subjects.find_one({"cycle": subject["cycle"]})
        if existing:
            # Mise à jour si le cycle existe déjà
            await db.subjects.update_one({"cycle": subject["cycle"]}, {"$set": subject})
            print(f"  [UPDATE] Cycle '{subject['cycle']}' mis à jour.")
        else:
            await db.subjects.insert_one(subject)
            print(f"  [OK] Cycle '{subject['cycle']}' ({subject['label']}) ajouté.")

    client.close()
    print("\n[SUCCESS] Seeding terminé ! La base LEFAXEUR est prête.")
    print("   Admin   : admin@lefaxeur.aero / admin2026")
    print("   Étudiant: user@lefaxeur.aero  / user2026")


if __name__ == "__main__":
    asyncio.run(seed())
