"""Настройки аккаунта: подключённые Яндекс/Google с календарём и пароль."""

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth.passwords import MIN_PASSWORD_LENGTH, hash_password, verify_password
from ..auth.providers import configured_providers, get_provider
from ..auth.router import UserOut, user_out
from ..calendar.service import invalidate_busy_cache, setup_calendars_in_background
from ..db import get_db
from ..models import OAuthAccount, User
from ..security import SESSION_COOKIE, current_user, destroy_other_sessions

router = APIRouter(prefix="/account", tags=["account"])


class ConnectionOut(BaseModel):
    provider: str
    title: str
    connected: bool
    email: str | None = None
    calendarAccess: bool = False
    syncEnabled: bool = False
    calendarStatus: str | None = None
    calendarError: str | None = None


def connection_out(provider_name: str, title: str, account: OAuthAccount | None) -> ConnectionOut:
    if not account:
        return ConnectionOut(provider=provider_name, title=title, connected=False)
    return ConnectionOut(
        provider=provider_name,
        title=title,
        connected=True,
        email=account.email,
        calendarAccess=account.calendar_access,
        syncEnabled=account.sync_enabled,
        calendarStatus=account.calendar_status if account.calendar_access else None,
        calendarError=account.calendar_error if account.calendar_access else None,
    )


@router.get("/connections", response_model=list[ConnectionOut])
def connections(user: User = Depends(current_user)) -> list[ConnectionOut]:
    """Все настроенные на сервере провайдеры и их состояние у пользователя."""
    return [connection_out(p.name, p.title, user.account(p.name)) for p in configured_providers()]


def _account_or_404(user: User, provider_name: str) -> OAuthAccount:
    provider = get_provider(provider_name)
    account = user.account(provider_name) if provider else None
    if not account:
        raise HTTPException(404, "Аккаунт не подключён")
    return account


class ConnectionPatch(BaseModel):
    syncEnabled: bool


@router.patch("/connections/{provider_name}", response_model=ConnectionOut)
def update_connection(
    provider_name: str,
    body: ConnectionPatch,
    background: BackgroundTasks,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ConnectionOut:
    account = _account_or_404(user, provider_name)
    if body.syncEnabled and not account.calendar_access:
        raise HTTPException(409, "Сначала выдайте доступ к календарю")
    account.sync_enabled = body.syncEnabled
    if body.syncEnabled and account.calendar_status == "error":
        account.calendar_status = "pending"  # дать ещё одну попытку
    db.commit()
    if body.syncEnabled:
        # Выгружаем уже существующие события в только что включённый календарь
        background.add_task(setup_calendars_in_background, user.id)
    provider = get_provider(provider_name)
    return connection_out(provider_name, provider.title if provider else provider_name, account)


@router.delete("/connections/{provider_name}", status_code=204)
def disconnect(provider_name: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    """Отключает аккаунт. События, уже выгруженные в его календарь, там остаются."""
    account = _account_or_404(user, provider_name)
    other_logins = [a for a in user.accounts if a is not account]
    if not user.password_hash and not other_logins:
        raise HTTPException(409, "Это единственный способ входа. Сначала задайте пароль или подключите другой аккаунт.")
    user.accounts.remove(account)
    db.commit()
    invalidate_busy_cache(user.id)


class SettingsPatch(BaseModel):
    confirmMode: Literal["confirm", "auto"]


@router.patch("/settings", response_model=UserOut)
def update_settings(body: SettingsPatch, user: User = Depends(current_user), db: Session = Depends(get_db)) -> UserOut:
    """Режим подтверждения: confirm — всё подтверждает пользователь; auto — создание и изменение сразу."""
    user.confirm_mode = body.confirmMode
    db.commit()
    return user_out(user)


class PasswordIn(BaseModel):
    currentPassword: str | None = Field(default=None, max_length=200)
    newPassword: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=200)


@router.post("/password", status_code=204)
def set_password(
    body: PasswordIn,
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    """Задать пароль (если входили только через Яндекс/Google) или сменить его."""
    if not user.email:
        raise HTTPException(409, "У аккаунта нет почты — вход по паролю невозможен")
    if user.password_hash and not verify_password(user.password_hash, body.currentPassword or ""):
        raise HTTPException(403, "Текущий пароль неверный")
    user.password_hash = hash_password(body.newPassword)
    # Остальные устройства выходят — на случай, если пароль меняют из-за утечки
    destroy_other_sessions(db, user, session)
    db.commit()
