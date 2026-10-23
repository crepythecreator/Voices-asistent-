"""OAuth-провайдеры: Яндекс ID и Google.

Один и тот же провайдер используется для входа (только профиль) и для подключения календаря
(дополнительные права). Права запрашиваются минимальные.

Яндекс: https://yandex.ru/dev/id/doc/ru/
Google: https://developers.google.com/identity/protocols/oauth2/web-server
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from ..config import settings
from ..db import utcnow


class OAuthError(Exception):
    def __init__(self, code: str, description: str = ""):
        super().__init__(f"{code}: {description}" if description else code)
        self.code = code


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None
    # Выданные права (через пробел)
    scope: str


@dataclass
class Profile:
    id: str
    email: str | None
    email_verified: bool
    name: str
    avatar_url: str | None


def new_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


class OAuthProvider:
    name: str
    title: str
    authorize_endpoint: str
    token_endpoint: str
    login_scopes: list[str]
    calendar_scopes: list[str]

    @property
    def client_id(self) -> str | None:
        return getattr(settings, f"{self.name}_client_id")

    @property
    def client_secret(self) -> str | None:
        return getattr(settings, f"{self.name}_client_secret")

    @property
    def redirect_uri(self) -> str:
        return getattr(settings, f"{self.name}_redirect_uri")

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def scopes(self, with_calendar: bool) -> list[str]:
        return self.login_scopes + (self.calendar_scopes if with_calendar else [])

    def has_calendar_access(self, granted_scope: str | None) -> bool:
        granted = set((granted_scope or "").split())
        return all(s in granted for s in self.calendar_scopes)

    def extra_authorize_params(self, with_calendar: bool) -> dict[str, str]:
        return {}

    def authorize_url(self, state: str, code_challenge: str, with_calendar: bool) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes(with_calendar)),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            **self.extra_authorize_params(with_calendar),
        }
        return f"{self.authorize_endpoint}?{urlencode(params)}"

    # --- Токены ---

    def _token_request(self, data: dict[str, str], requested_scope: str) -> TokenSet:
        try:
            resp = self._post_token(data)
        except httpx.HTTPError as e:
            raise OAuthError("network_error", str(e)) from e
        body: dict[str, Any] = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if resp.status_code != 200 or "access_token" not in body:
            raise OAuthError(body.get("error", "token_error"), body.get("error_description", resp.text[:300]))
        expires_in = body.get("expires_in")
        return TokenSet(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token"),
            expires_at=utcnow() + timedelta(seconds=int(expires_in)) if expires_in else None,
            # Если провайдер не вернул scope — выданы все запрошенные права
            scope=body.get("scope") or requested_scope,
        )

    def _post_token(self, data: dict[str, str]) -> httpx.Response:
        return httpx.post(self.token_endpoint, data=data, auth=(self.client_id or "", self.client_secret or ""), timeout=15)

    def exchange_code(self, code: str, code_verifier: str, with_calendar: bool) -> TokenSet:
        return self._token_request(
            {
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": self.redirect_uri,
            },
            " ".join(self.scopes(with_calendar)),
        )

    def refresh(self, refresh_token: str, current_scope: str | None) -> TokenSet:
        return self._token_request({"grant_type": "refresh_token", "refresh_token": refresh_token}, current_scope or "")

    def fetch_profile(self, access_token: str) -> Profile:
        raise NotImplementedError


class YandexProvider(OAuthProvider):
    name = "yandex"
    title = "Яндекс ID"
    authorize_endpoint = "https://oauth.yandex.ru/authorize"
    token_endpoint = "https://oauth.yandex.ru/token"
    login_scopes = ["login:info", "login:email"]
    # С правом calendar:events.write CalDAV отвечает 401 — нужен полный доступ к Календарю
    calendar_scopes = ["calendar:all"]

    def extra_authorize_params(self, with_calendar: bool) -> dict[str, str]:
        # При подключении календаря показываем экран согласия заново, чтобы выдать новое право
        return {"force_confirm": "yes"} if with_calendar else {}

    def fetch_profile(self, access_token: str) -> Profile:
        try:
            resp = httpx.get(
                "https://login.yandex.ru/info",
                params={"format": "json"},
                headers={"Authorization": f"OAuth {access_token}"},
                timeout=15,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise OAuthError("userinfo_error", str(e)) from e
        info = resp.json()
        avatar_id = None if info.get("is_avatar_empty", True) else info.get("default_avatar_id")
        email = info.get("default_email")
        return Profile(
            id=str(info["id"]),
            email=email,
            # Яндекс отдаёт только подтверждённые адреса
            email_verified=bool(email),
            name=info.get("display_name") or info.get("real_name") or info["login"],
            avatar_url=f"https://avatars.yandex.net/get-yapic/{avatar_id}/islands-200" if avatar_id else None,
        )


class GoogleProvider(OAuthProvider):
    name = "google"
    title = "Google"
    authorize_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint = "https://oauth2.googleapis.com/token"
    login_scopes = ["openid", "email", "profile"]
    calendar_scopes = [
        # Создать свой календарь и управлять событиями только в нём
        "https://www.googleapis.com/auth/calendar.app.created",
        # Только чтение остальных календарей — для занятости
        "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
        "https://www.googleapis.com/auth/calendar.events.readonly",
    ]

    def has_calendar_access(self, granted_scope: str | None) -> bool:
        # Пользователь может снять галочки с части прав — без записи в свой календарь синхронизация не нужна
        return self.calendar_scopes[0] in set((granted_scope or "").split())

    def extra_authorize_params(self, with_calendar: bool) -> dict[str, str]:
        if with_calendar:
            # refresh_token Google отдаёт только при access_type=offline и явном согласии
            return {"access_type": "offline", "prompt": "consent", "include_granted_scopes": "true"}
        return {"prompt": "select_account"}

    def _post_token(self, data: dict[str, str]) -> httpx.Response:
        body = {**data, "client_id": self.client_id or "", "client_secret": self.client_secret or ""}
        return httpx.post(self.token_endpoint, data=body, timeout=15)

    def refresh(self, refresh_token: str, current_scope: str | None) -> TokenSet:
        # redirect_uri при обновлении Google не нужен
        return self._token_request({"grant_type": "refresh_token", "refresh_token": refresh_token}, current_scope or "")

    def fetch_profile(self, access_token: str) -> Profile:
        try:
            resp = httpx.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise OAuthError("userinfo_error", str(e)) from e
        info = resp.json()
        return Profile(
            id=str(info["sub"]),
            email=info.get("email"),
            email_verified=bool(info.get("email_verified")),
            name=info.get("name") or info.get("email") or "Пользователь Google",
            avatar_url=info.get("picture"),
        )


PROVIDERS: dict[str, OAuthProvider] = {p.name: p for p in (YandexProvider(), GoogleProvider())}


def get_provider(name: str) -> OAuthProvider | None:
    return PROVIDERS.get(name)


def configured_providers() -> list[OAuthProvider]:
    return [p for p in PROVIDERS.values() if p.is_configured()]
