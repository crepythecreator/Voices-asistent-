import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Query, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..calendar.service import setup_calendar_in_background
from ..config import settings
from ..db import get_db
from ..models import User
from ..security import SESSION_COOKIE, create_session, current_user, destroy_session, seal, unseal
from . import yandex

log = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

STATE_COOKIE = "oauth_state"
STATE_TTL_SECONDS = 600


class UserOut(BaseModel):
    id: str
    name: str
    email: str | None
    avatarUrl: str | None


def user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        name=user.display_name,
        email=user.email,
        avatarUrl=yandex.avatar_url(user.avatar_id),
    )


def safe_next(path: str | None) -> str:
    """Только относительные пути внутри фронта — защита от open redirect."""
    if not path or not path.startswith("/") or path.startswith("//") or path.startswith("/\\"):
        return "/"
    return path


def frontend_redirect(path: str) -> RedirectResponse:
    return RedirectResponse(f"{settings.frontend_url.rstrip('/')}{path}", status_code=302)


def login_error(code: str) -> RedirectResponse:
    resp = frontend_redirect(f"/login?{urlencode({'error': code})}")
    resp.delete_cookie(STATE_COOKIE, path="/")
    return resp


@router.get("/yandex/login")
def yandex_login(next: str | None = Query(default=None)) -> RedirectResponse:
    if not yandex.is_configured():
        raise HTTPException(503, "Не заданы YANDEX_CLIENT_ID / YANDEX_CLIENT_SECRET")

    state = secrets.token_urlsafe(24)
    verifier, challenge = yandex.new_pkce_pair()
    resp = RedirectResponse(yandex.authorize_url(state, challenge), status_code=302)
    # state, PKCE verifier и адрес возврата — в зашифрованной cookie на 10 минут
    resp.set_cookie(
        STATE_COOKIE,
        seal({"state": state, "verifier": verifier, "next": safe_next(next)}),
        max_age=STATE_TTL_SECONDS,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return resp


@router.get("/yandex/callback")
def yandex_callback(
    background: BackgroundTasks,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(default=None, alias=STATE_COOKIE),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if error:
        return login_error("access_denied" if error == "access_denied" else error)

    saved = unseal(oauth_state, STATE_TTL_SECONDS) if oauth_state else None
    if not saved or not state or not secrets.compare_digest(saved["state"], state) or not code:
        return login_error("invalid_state")

    try:
        tokens = yandex.exchange_code(code, saved["verifier"])
        profile = yandex.fetch_profile(tokens.access_token)
    except yandex.YandexOAuthError as e:
        log.warning("Yandex OAuth failed: %s", e)
        return login_error(e.code)

    user = db.scalar(select(User).where(User.yandex_id == profile.id))
    if not user:
        user = User(yandex_id=profile.id, timezone=settings.app_timezone)
        db.add(user)
    user.login = profile.login
    user.email = profile.email
    user.display_name = profile.display_name
    user.avatar_id = profile.avatar_id
    db.flush()
    yandex.save_tokens(db, user, tokens)
    db.commit()

    resp = frontend_redirect(saved["next"])
    resp.delete_cookie(STATE_COOKIE, path="/")
    create_session(db, user, resp)
    # Отдельный календарь в Яндексе создаём в фоне, чтобы не задерживать вход
    background.add_task(setup_calendar_in_background, user.id)
    return resp


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
