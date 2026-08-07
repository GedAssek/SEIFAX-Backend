"""
LEFAXEUR - Point d'entrée principal de l'API FastAPI
Lancer avec : uvicorn app:app --reload
Documentation auto : http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from database.db import connect_db, close_db
from routes import auth, epreuves, infos, subjects, documents, admin


# ─── Cycle de vie de l'application ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


# ─── Création de l'application ──────────────────────────────────────────────
app = FastAPI(
    title="LEFAXEUR API",
    description="API Backend pour la plateforme de ressources étudiantes LEFAXEUR",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# ─── CORS (Permettre au Frontend de communiquer avec le Backend) ─────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://seifax-frontend.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Servir les fichiers uploadés (PDF) ─────────────────────────────────────
os.makedirs("uploads/epreuves", exist_ok=True)
os.makedirs("uploads/infos", exist_ok=True)
os.makedirs("uploads/documents", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ─── Inclusion des routes ───────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api")
app.include_router(epreuves.router, prefix="/api")
app.include_router(infos.router, prefix="/api")
app.include_router(subjects.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


# ─── Route racine (test de santé) ───────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name": "LEFAXEUR API",
        "version": "1.0.0",
        "status": "✅ En ligne",
        "docs": "/docs"
    }
