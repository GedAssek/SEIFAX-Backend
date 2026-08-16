"""
LEFAXEUR - Point d'entrée principal de l'API FastAPI
Lancer avec : uvicorn app:app --reload
Documentation auto : http://localhost:8000/docs
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import logging

from database.db import connect_db, close_db
from routes import auth, epreuves, infos, subjects, documents, admin, heures
import asyncio
from utils.sync_drive import sync_drive_to_db


# ─── Tâche de synchronisation en arrière-plan ─────────────────────────────────
async def background_sync_task():
    while True:
        print("[Background Sync] Lancement de la synchronisation Drive...")
        success, message = await sync_drive_to_db()
        print(f"[Background Sync] Résultat: {message}")
        # La première synchronisation est immédiate ; les suivantes ont lieu
        # toutes les 12 heures (43200 secondes).
        await asyncio.sleep(43200)

# ─── Cycle de vie de l'application ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    task = asyncio.create_task(background_sync_task())
    yield
    task.cancel()
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
# Autoriser toutes les origines pour assurer la compatibilité (GitHub Pages, Live Server, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "ALLOWED_ORIGINS", "https://gedassek.github.io,http://localhost:5500,http://127.0.0.1:5500"
    ).split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > int(os.getenv("MAX_UPLOAD_BYTES", 10 * 1024 * 1024)):
        return JSONResponse(status_code=413, content={"detail": "Requête trop volumineuse"})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.exception("Unhandled API error for %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur"})


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
app.include_router(heures.router, prefix="/api")


# ─── Route racine (test de santé) ───────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name": "LEFAXEUR API",
        "version": "1.0.0",
        "status": "✅ En ligne",
        "docs": "/docs"
    }
