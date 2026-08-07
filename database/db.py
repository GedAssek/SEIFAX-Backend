"""
LEFAXEUR - Connexion à la base de données MongoDB (via Motor - async)
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "lefaxeur_db")

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    """Initialise la connexion à MongoDB."""
    global client, db
    # Create a new client and connect to the server
    client = AsyncIOMotorClient(MONGODB_URL, server_api=ServerApi('1'))
    db = client[DB_NAME]
    
    # Send a ping to confirm a successful connection
    try:
        await client.admin.command('ping')
        print(f"[OK] Pinged your deployment. Connecté à MongoDB : {DB_NAME}")
    except Exception as e:
        print(f"[ERROR] Erreur de connexion MongoDB : {e}")


async def close_db():
    """Ferme la connexion à MongoDB."""
    global client
    if client:
        client.close()
        print("[CLOSE] Connexion MongoDB fermee.")


def get_db():
    """Retourne l'instance de la base de données."""
    return db
