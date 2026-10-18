"""Клиент OAuth Яндекс ID: https://yandex.ru/dev/id/doc/ru/"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..db import as_utc, utcnow
from ..models import User, YandexToken
from ..security import decrypt, encrypt

AUTHORIZE_URL = "https://oauth.yandex.ru/authorize"
TOKEN_URL = "https://oauth.yandex.ru/token"
USER_INFO_URL = "https://login.yandex.ru/info"
AVATAR_URL = "https://avatars.yandex.net/get-yapic/{avatar_id}/islands-200"

# Обновляем токен заранее, чтобы он не истёк посреди запроса к CalDAV
REFRESH_MARGIN = timedelta(minutes=5)


class YandexOAuthError(Exception):
    def __init__(self, code: str, description: str = ""):
        super().__init__(f"{code}: {description}" if description else code)
        self.code = code


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None
    scope: str | None


@dataclass
class YandexProfile:
    id: str
    login: str
    email: str | None
    display_name: str
    avatar_id: str | None


def is_configured() -> bool:
    return bool(settings.yandex_client_id and settings.yandex_client_secret)


def new_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def authorize_url(state: str, code_challenge: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.yandex_client_id,
        "redirect_uri": settings.yandex_redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    if settings.yandex_oauth_scope:
        params["scope"] = settings.yandex_oauth_scope
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def _token_request(data: dict[str, str]) -> TokenSet:
    try:
        resp = httpx.post(
            TOKEN_URL,
            data=data,
            auth=(settings.yandex_client_id or "", settings.yandex_client_secret or ""),
            timeout=15,
        )
    except httpx.HTTPError as e:
        raise YandexOAuthError("network_error", str(e)) from e
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if resp.status_code != 200 or "access_token" not in body:
        raise YandexOAuthError(body.get("error", "token_error"), body.get("error_description", resp.text))
    expires_in = body.get("expires_in")
    return TokenSet(
        access_token=body["access_token"],
        refresh_token=body.get("refresh_token"),
        expires_at=utcnow() + timedelta(seconds=int(expires_in)) if expires_in else None,
        scope=body.get("scope"),
    )


def exchange_code(code: str, code_verifier: str) -> TokenSet:
    return _token_request({"grant_type": "authorization_code", "code": code, "code_verifier": code_verifier})


def refresh(refresh_token: str) -> TokenSet:
    return _token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})


def fetch_profile(access_token: str) -> YandexProfile:
    try:
        resp = httpx.get(
            USER_INFO_URL,
            params={"format": "json"},
            headers={"Authorization": f"OAuth {access_token}"},
            timeout=15,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise YandexOAuthError("userinfo_error", str(e)) from e
    info = resp.json()
    avatar_id = None if info.get("is_avatar_empty", True) else info.get("default_avatar_id")
    return YandexProfile(
        id=str(info["id"]),
        login=info["login"],
        email=info.get("default_email"),
        display_name=info.get("display_name") or info.get("real_name") or info["login"],
        avatar_id=avatar_id,
    )


def avatar_url(avatar_id: str | None) -> str | None:
    return AVATAR_URL.format(avatar_id=avatar_id) if avatar_id else None


def save_tokens(db: Session, user: User, tokens: TokenSet) -> None:
    row = user.token or YandexToken(user_id=user.id)
    row.access_token_enc = encrypt(tokens.access_token)
    # Яндекс может не вернуть новый refresh_token — тогда оставляем прежний
    if tokens.refresh_token:
        row.refresh_token_enc = encrypt(tokens.refresh_token)
    row.expires_at = tokens.expires_at
    row.scope = tokens.scope
    user.token = row


def get_access_token(db: Session, user: User) -> str | None:
    """Действующий токен пользователя; при необходимости обновляет его. None — токена нет или он отозван."""
    row = user.token
    if not row:
        return None
    if row.expires_at and as_utc(row.expires_at) - REFRESH_MARGIN <= utcnow():
        if not row.refresh_token_enc:
            return None
        try:
            save_tokens(db, user, refresh(decrypt(row.refresh_token_enc)))
            db.commit()
        except YandexOAuthError:
            return None
    return decrypt(user.token.access_token_enc)  # type: ignore[union-attr]
