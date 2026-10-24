import logging
import secrets
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..calendar.service import setup_calendars_in_background
from ..config import settings
from ..db import get_db
from ..models import User
from ..security import SESSION_COOKIE, create_session, current_user, destroy_session, seal, session_user, unseal
from . import accounts
from .passwords import MIN_PASSWORD_LENGTH, hash_password, login_limiter, normalize_email, verify_password
from .providers import PROVIDERS, OAuthError, OAuthProvider, get_provider, new_pkce_pair

log = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

STATE_COOKIE = "oauth_state"
STATE_TTL_SECONDS = 600


class UserOut(BaseModel):
    id: str
    name: str
    email: str | None
    avatarUrl: str | None
    hasPassword: bool
    confirmMode: Literal["confirm", "auto"]


def user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        name=user.display_name,
        email=user.email,
        avatarUrl=user.avatar_url,
        hasPassword=bool(user.password_hash),
        confirmMode="auto" if user.confirm_mode == "auto" else "confirm",
    )


def safe_next(path: str | None, default: str = "/") -> str:
    """Только относительные пути внутри фронта — защита от open redirect."""
    if not path or not path.startswith("/") or path.startswith("//") or path.startswith("/\\"):
        return default
    return path


def frontend_redirect(path: str) -> RedirectResponse:
    resp = RedirectResponse(f"{settings.frontend_url.rstrip('/')}{path}", status_code=302)
    resp.delete_cookie(STATE_COOKIE, path="/")
    return resp


def _provider_or_404(name: str) -> OAuthProvider:
    provider = get_provider(name)
    if not provider:
        raise HTTPException(404, "Неизвестный провайдер")
    if not provider.is_configured():
        raise HTTPException(503, f"Вход через {provider.title} не настроен на сервере")
    return provider


# --- Почта и пароль -----------------------------------------------------------------------


class ProviderOut(BaseModel):
    id: str
    title: str
    # false — на сервере не заданы ключи; кнопку показываем, но она неактивна
    configured: bool


@router.get("/providers", response_model=list[ProviderOut])
def providers() -> list[ProviderOut]:
    """Все провайдеры для кнопок на странице входа и признак, настроены ли они на сервере."""
    return [ProviderOut(id=p.name, title=p.title, configured=p.is_configured()) for p in PROVIDERS.values()]


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=200)
    name: str = Field(min_length=1, max_length=100)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=200)


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)) -> UserOut:
    email = normalize_email(body.email)
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "Эта почта уже зарегистрирована. Войдите по паролю или через Яндекс/Google.")
    user = User(
        email=email,
        email_verified=False,
        password_hash=hash_password(body.password),
        display_name=body.name.strip(),
        timezone=settings.app_timezone,
    )
    db.add(user)
    db.commit()
    create_session(db, user, response)
    return user_out(user)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> UserOut:
    email = normalize_email(body.email) or ""
    keys = (f"email:{email}", f"ip:{request.client.host if request.client else '-'}")
    if login_limiter.blocked(*keys):
        raise HTTPException(429, "Слишком много попыток входа. Попробуйте через 15 минут.")
    user = db.scalar(select(User).where(User.email == email))
    if not verify_password(user.password_hash if user else None, body.password):
        login_limiter.fail(*keys)
        raise HTTPException(401, "Неверная почта или пароль")
    login_limiter.reset(keys[0])
    create_session(db, user, response)  # type: ignore[arg-type]
    return user_out(user)  # type: ignore[arg-type]


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return user_out(user)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> None:
    destroy_session(db, session, response)


# --- OAuth: вход и подключение --------------------------------------------------------------


def _start_oauth(provider: OAuthProvider, purpose: Literal["login", "connect"], next_path: str, user_id: str | None) -> RedirectResponse:
    state = secrets.token_urlsafe(24)
    verifier, challenge = new_pkce_pair()
    with_calendar = purpose == "connect"
    resp = RedirectResponse(provider.authorize_url(state, challenge, with_calendar=with_calendar), status_code=302)
    # state, PKCE verifier, цель и адрес возврата — в зашифрованной cookie на 10 минут
    resp.set_cookie(
        STATE_COOKIE,
        seal({"state": state, "verifier": verifier, "next": next_path, "purpose": purpose, "user_id": user_id, "provider": provider.name}),
        max_age=STATE_TTL_SECONDS,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return resp


@router.get("/{provider_name}/login")
def oauth_login(provider_name: str, next: str | None = Query(default=None)) -> RedirectResponse:
    """Вход или регистрация через Яндекс/Google (только профиль, без календаря)."""
    return _start_oauth(_provider_or_404(provider_name), "login", safe_next(next), None)


@router.get("/{provider_name}/connect")
def oauth_connect(
    provider_name: str,
    next: str | None = Query(default=None),
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Подключение аккаунта с доступом к календарю — из настроек, для вошедшего пользователя."""
    provider = _provider_or_404(provider_name)
    user = session_user(db, session)
    if not user:
        return frontend_redirect(f"/login?{urlencode({'next': '/settings'})}")
    return _start_oauth(provider, "connect", safe_next(next, "/settings"), str(user.id))


@router.get("/{provider_name}/callback")
def oauth_callback(
    provider_name: str,
    background: BackgroundTasks,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(default=None, alias=STATE_COOKIE),
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    saved = unseal(oauth_state, STATE_TTL_SECONDS) if oauth_state else None
    connecting = bool(saved and saved.get("purpose") == "connect")
    fail_page = saved["next"] if connecting and saved else "/login"

    def fail(code_: str) -> RedirectResponse:
        return frontend_redirect(f"{fail_page}?{urlencode({'error': code_, 'provider': provider_name})}")

    if error:
        return fail("access_denied" if error == "access_denied" else "provider_error")
    provider = get_provider(provider_name)
    if (
        not provider
        or not saved
        or saved.get("provider") != provider_name
        or not state
        or not secrets.compare_digest(saved["state"], state)
        or not code
    ):
        return fail("invalid_state")

    try:
        tokens = provider.exchange_code(code, saved["verifier"], with_calendar=connecting)
        profile = provider.fetch_profile(tokens.access_token)

        if connecting:
            user = session_user(db, session)
            if not user or str(user.id) != saved.get("user_id"):
                return fail("invalid_state")
            accounts.connect_provider(db, user, provider, tokens, profile)
            db.commit()
            background.add_task(setup_calendars_in_background, user.id)
            return frontend_redirect(f"{saved['next']}?{urlencode({'connected': provider_name})}")

        user = accounts.login_with_provider(db, provider, tokens, profile)
        if not user.timezone:
            user.timezone = settings.app_timezone
        db.commit()
    except OAuthError as e:
        db.rollback()
        log.warning("OAuth %s failed: %s", provider_name, e)
        return fail(e.code if e.code in {"already_linked", "other_account_connected"} else "provider_error")

    resp = frontend_redirect(saved["next"])
    create_session(db, user, resp)
    background.add_task(setup_calendars_in_background, user.id)
    return resp
