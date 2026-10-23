"""Вход и подключение аккаунтов через OAuth, хранение токенов.

Правило связки: вход через провайдера с подтверждённой почтой попадает в существующий аккаунт
с этой почтой. Если почта того аккаунта не была подтверждена (регистрация по паролю без письма),
пароль сбрасывается, а его сессии завершаются — иначе кто-то мог бы заранее зарегистрироваться
на чужую почту и получить доступ к аккаунту после того, как владелец войдёт через Google/Яндекс.
"""

import logging
from datetime import timedelta

from cryptography.fernet import InvalidToken
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db import as_utc, utcnow
from ..models import AuthSession, OAuthAccount, User
from ..security import decrypt, encrypt
from .passwords import normalize_email
from .providers import OAuthError, OAuthProvider, Profile, TokenSet, get_provider

log = logging.getLogger(__name__)

# Обновляем токен заранее, чтобы он не истёк посреди запроса к календарю
REFRESH_MARGIN = timedelta(minutes=5)


def save_tokens(account: OAuthAccount, tokens: TokenSet, provider: OAuthProvider) -> None:
    account.access_token_enc = encrypt(tokens.access_token)
    # Провайдер может не вернуть новый refresh_token — тогда оставляем прежний
    if tokens.refresh_token:
        account.refresh_token_enc = encrypt(tokens.refresh_token)
    account.expires_at = tokens.expires_at
    account.scope = tokens.scope
    account.calendar_access = provider.has_calendar_access(tokens.scope)
    if not account.calendar_access:
        account.sync_enabled = False


def get_access_token(db: Session, account: OAuthAccount) -> str | None:
    """Действующий токен аккаунта; при необходимости обновляет его. None — токен недоступен."""
    provider = get_provider(account.provider)
    if not provider or not account.access_token_enc:
        return None
    if account.expires_at and as_utc(account.expires_at) - REFRESH_MARGIN <= utcnow():
        if not account.refresh_token_enc:
            return None
        try:
            save_tokens(account, provider.refresh(decrypt(account.refresh_token_enc), account.scope), provider)
            db.commit()
        except (OAuthError, InvalidToken) as e:
            log.warning("Не удалось обновить токен %s: %s", account.provider, e)
            return None
    try:
        return decrypt(account.access_token_enc)
    except InvalidToken:
        # Сменили APP_SECRET_KEY — старые токены не расшифровать, нужно переподключить аккаунт
        log.warning("Токен %s не расшифровывается — переподключите аккаунт", account.provider)
        return None


def _find_account(db: Session, provider: str, provider_user_id: str) -> OAuthAccount | None:
    return db.scalar(
        select(OAuthAccount).where(OAuthAccount.provider == provider, OAuthAccount.provider_user_id == provider_user_id)
    )


def _email_free(db: Session, email: str | None) -> bool:
    return bool(email) and db.scalar(select(User.id).where(User.email == email)) is None


def login_with_provider(db: Session, provider: OAuthProvider, tokens: TokenSet, profile: Profile) -> User:
    """Вход или регистрация через провайдера. Возвращает пользователя (изменения не закоммичены)."""
    account = _find_account(db, provider.name, profile.id)
    if account:
        user = account.user
        account.email = normalize_email(profile.email)
        # Токены уже подключённого аккаунта не трогаем: при входе запрашиваются только права на профиль,
        # и мы потеряли бы доступ к календарю
        if not user.avatar_url:
            user.avatar_url = profile.avatar_url
        return user

    email = normalize_email(profile.email)
    user = None
    if email and profile.email_verified:
        user = db.scalar(select(User).where(User.email == email))
        if user and not user.email_verified:
            if user.password_hash:
                log.info("Связка %s с аккаунтом %s: пароль сброшен (почта не была подтверждена)", provider.name, user.id)
            user.password_hash = None
            db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
        if user:
            user.email_verified = True
            if user.account(provider.name):
                # К аккаунту уже привязан другой аккаунт этого провайдера
                raise OAuthError("other_account_connected")

    if not user:
        user = User(
            email=email if _email_free(db, email) else None,
            email_verified=bool(email and profile.email_verified),
            display_name=profile.name,
            avatar_url=profile.avatar_url,
        )
        db.add(user)
        db.flush()

    _attach(db, user, provider, tokens, profile)
    return user


def connect_provider(db: Session, user: User, provider: OAuthProvider, tokens: TokenSet, profile: Profile) -> OAuthAccount:
    """Подключение аккаунта провайдера (с календарём) к уже вошедшему пользователю."""
    existing = _find_account(db, provider.name, profile.id)
    if existing and existing.user_id != user.id:
        raise OAuthError("already_linked")
    mine = user.account(provider.name)
    if mine and mine.provider_user_id != profile.id:
        raise OAuthError("other_account_connected")

    account = mine or _attach(db, user, provider, tokens, profile)
    had_calendar = account.calendar_access if mine else False
    account.email = normalize_email(profile.email)
    save_tokens(account, tokens, provider)
    if account.calendar_access and not had_calendar:
        account.sync_enabled = True  # только что выдали доступ — сразу включаем синхронизацию
        account.calendar_status, account.calendar_error = "pending", None
    if not user.email and profile.email_verified and _email_free(db, normalize_email(profile.email)):
        user.email, user.email_verified = normalize_email(profile.email), True
    if not user.avatar_url:
        user.avatar_url = profile.avatar_url
    return account


def _attach(db: Session, user: User, provider: OAuthProvider, tokens: TokenSet, profile: Profile) -> OAuthAccount:
    account = OAuthAccount(
        user_id=user.id,
        provider=provider.name,
        provider_user_id=profile.id,
        email=normalize_email(profile.email),
    )
    save_tokens(account, tokens, provider)
    account.sync_enabled = account.calendar_access
    user.accounts.append(account)
    db.flush()
    return account
