"""Шифрование секретов и сессии пользователей."""

import base64
import hashlib
import json
import secrets
from datetime import timedelta
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Cookie, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import settings
from .db import as_utc, get_db, utcnow
from .models import AuthSession, User

SESSION_COOKIE = "session"

_fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(settings.app_secret_key.encode()).digest()))


def encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet.decrypt(value.encode()).decode()


def seal(data: dict[str, Any]) -> str:
    """Зашифрованный и подписанный JSON — для короткоживущих cookie (OAuth state)."""
    return encrypt(json.dumps(data))


def unseal(token: str, max_age_seconds: int) -> dict[str, Any] | None:
    try:
        return json.loads(_fernet.decrypt(token.encode(), ttl=max_age_seconds))
    except (InvalidToken, ValueError):
        return None


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    ttl = timedelta(days=settings.session_ttl_days)
    db.add(AuthSession(id=_hash(token), user_id=user.id, expires_at=utcnow() + ttl))
    db.commit()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(ttl.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def destroy_session(db: Session, token: str | None, response: Response) -> None:
    if token:
        db.execute(delete(AuthSession).where(AuthSession.id == _hash(token)))
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


def current_user(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> User:
    if not session:
        raise HTTPException(401, "Требуется вход")
    row = db.scalar(select(AuthSession).where(AuthSession.id == _hash(session)))
    if not row or as_utc(row.expires_at) <= utcnow():
        raise HTTPException(401, "Сессия истекла")
    return row.user
