"""Security helpers shared by API routes."""
from __future__ import annotations

import os
import secrets
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 10 * 1024 * 1024))
_login_attempts: dict[str, deque[datetime]] = defaultdict(deque)
LOGIN_WINDOW = timedelta(minutes=int(os.getenv("LOGIN_RATE_WINDOW_MINUTES", "15")))
# Five failed attempts in the time window lock further attempts.  Keep this
# fixed so a deployment environment cannot accidentally weaken the policy.
LOGIN_MAX_ATTEMPTS = 5


def _recent_attempts(key: str) -> deque[datetime]:
    now = datetime.now(timezone.utc)
    attempts = _login_attempts[key]
    while attempts and now - attempts[0] > LOGIN_WINDOW:
        attempts.popleft()
    return attempts


def ensure_login_allowed(key: str) -> None:
    if len(_recent_attempts(key)) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives. Réessayez plus tard.",
            headers={"Retry-After": str(int(LOGIN_WINDOW.total_seconds()))},
        )


def record_failed_login(key: str) -> None:
    _recent_attempts(key).append(datetime.now(timezone.utc))


def clear_failed_logins(key: str) -> None:
    _login_attempts.pop(key, None)


async def ensure_persistent_login_allowed(db, username: str) -> None:
    """Check a MongoDB-backed lock, shared across server instances."""
    now = datetime.utcnow()
    attempt = await db.login_attempts.find_one({"username": username.lower()})
    if not attempt:
        return
    locked_until = attempt.get("locked_until")
    if locked_until and locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(max(1, int((locked_until - now).total_seconds())))},
        )
    if attempt.get("first_failure", now) + LOGIN_WINDOW <= now:
        await db.login_attempts.delete_one({"_id": attempt["_id"]})


async def record_persistent_failed_login(db, username: str, client_ip: str) -> None:
    """Record a failed attempt and lock the account after five failures."""
    now = datetime.utcnow()
    key = username.lower()
    attempt = await db.login_attempts.find_one({"username": key})
    if not attempt or attempt.get("first_failure", now) + LOGIN_WINDOW <= now:
        await db.login_attempts.update_one(
            {"username": key},
            {"$set": {"username": key, "first_failure": now, "failures": 1,
                      "last_ip": client_ip, "expires_at": now + LOGIN_WINDOW},
             "$unset": {"locked_until": ""}},
            upsert=True,
        )
        return
    failures = attempt.get("failures", 0) + 1
    update = {"failures": failures, "last_ip": client_ip, "expires_at": now + LOGIN_WINDOW}
    if failures >= LOGIN_MAX_ATTEMPTS:
        update["locked_until"] = now + LOGIN_WINDOW
    await db.login_attempts.update_one({"_id": attempt["_id"]}, {"$set": update})


async def clear_persistent_failed_logins(db, username: str) -> None:
    await db.login_attempts.delete_one({"username": username.lower()})


def safe_object_id(value: str):
    """Return a Mongo ObjectId or a safe 404 rather than an internal error."""
    from bson import ObjectId

    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=404, detail="Ressource introuvable")
    return ObjectId(value)


async def save_validated_upload(
    upload: UploadFile,
    directory: str,
    allowed_signatures: dict[str, tuple[bytes, ...]],
) -> tuple[str, str]:
    """Validate extension, magic bytes and size before writing a randomized name."""
    extension = Path(upload.filename or "").suffix.lower()
    if extension not in allowed_signatures:
        raise HTTPException(status_code=400, detail="Type de fichier non autorisé")

    first_chunk = await upload.read(8192)
    if not first_chunk or not any(first_chunk.startswith(sig) for sig in allowed_signatures[extension]):
        raise HTTPException(status_code=400, detail="Le contenu du fichier ne correspond pas au type annoncé")

    os.makedirs(directory, exist_ok=True)
    filename = f"{secrets.token_urlsafe(18)}{extension}"
    path = os.path.join(directory, filename)
    total = 0
    try:
        with open(path, "xb") as handle:
            for chunk in (first_chunk,):
                total += len(chunk)
                handle.write(chunk)
            while chunk := await upload.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Fichier trop volumineux")
                handle.write(chunk)
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        raise
    finally:
        await upload.close()
    return filename, path


PDF_SIGNATURES = {".pdf": (b"%PDF-",)}
INFO_SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".webp": (b"RIFF",),
}
