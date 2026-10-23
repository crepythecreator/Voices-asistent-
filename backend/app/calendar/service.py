"""Наши события и их выгрузка в календари подключённых аккаунтов (Яндекс, Google).

Источник правды — наша БД. Событие выгружается в каждый аккаунт с доступом к календарю и
включённой синхронизацией (отдельный календарь ассистента у провайдера). Ошибка выгрузки не
откатывает изменение, а помечается в event_syncs; повтор — POST /calendar/sync.
Занятость читается из всех календарей всех аккаунтов с доступом — только чтение.
"""

import logging
import time
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.accounts import get_access_token
from ..config import settings
from ..db import SessionLocal, as_utc
from ..models import Event, EventSync, OAuthAccount, User
from .backend import CalendarBackend, CalendarError
from .google_calendar import GoogleCalendarClient
from .ical import ExternalEvent
from .yandex_caldav import YandexCalendarClient

log = logging.getLogger(__name__)

# Занятость кешируем ненадолго: запросы к календарям медленные
BUSY_CACHE_TTL = 60
_busy_cache: dict[tuple[uuid.UUID, datetime, datetime], tuple[float, list[ExternalEvent]]] = {}


def backend_for(db: Session, user: User, account: OAuthAccount) -> CalendarBackend | None:
    """Клиент календаря аккаунта. None — нет действующего токена."""
    if not account.calendar_access:
        return None
    token = get_access_token(db, account)
    if not token:
        return None
    if account.provider == "yandex":
        return YandexCalendarClient(account.email or user.email or "", token)
    if account.provider == "google":
        return GoogleCalendarClient(token, user.timezone)
    return None


def sync_accounts(user: User) -> list[OAuthAccount]:
    """Аккаунты, в чьи календари выгружаем события ассистента."""
    return [a for a in user.accounts if a.calendar_access and a.sync_enabled]


def _ensure_calendar(db: Session, account: OAuthAccount, backend: CalendarBackend) -> str:
    if account.calendar_status == "ok" and account.calendar_id:
        return account.calendar_id
    try:
        account.calendar_id = backend.ensure_calendar(settings.calendar_name, account.calendar_id)
        account.calendar_status, account.calendar_error = "ok", None
    except CalendarError as e:
        account.calendar_status, account.calendar_error = "error", str(e)[:1000]
        raise
    finally:
        db.flush()
    return account.calendar_id


def _sync_record(event: Event, account: OAuthAccount) -> EventSync | None:
    return next((s for s in event.syncs if s.account_id == account.id), None)


def _sync_to(db: Session, user: User, event: Event, account: OAuthAccount) -> None:
    rec = _sync_record(event, account)
    if rec is None:
        rec = EventSync(event_id=event.id, account_id=account.id)
        event.syncs.append(rec)
    backend = backend_for(db, user, account)
    if not backend:
        rec.status, rec.error = "error", "Нет доступа к календарю — переподключите аккаунт в настройках"
        return
    try:
        calendar_id = _ensure_calendar(db, account, backend)
        rec.remote_id = backend.upsert_event(calendar_id, event, rec.remote_id)
        rec.status, rec.error = "synced", None
    except CalendarError as e:
        log.warning("Выгрузка события %s в %s не удалась: %s", event.id, account.provider, e)
        rec.status, rec.error = "error", str(e)[:1000]


def sync_event(db: Session, user: User, event: Event) -> None:
    """Выгружает событие во все включённые календари (создание или изменение)."""
    for account in sync_accounts(user):
        _sync_to(db, user, event, account)
    db.flush()


def unsync_event(db: Session, user: User, event: Event) -> None:
    """Удаляет копии события у провайдеров. Ошибки только логируем — локально событие уже удаляется."""
    for rec in event.syncs:
        account = rec.account
        if rec.status != "synced" or not rec.remote_id or not account.calendar_id:
            continue
        backend = backend_for(db, user, account)
        if not backend:
            continue
        try:
            backend.delete_event(account.calendar_id, rec.remote_id)
        except CalendarError as e:
            log.warning("Не удалось удалить событие %s из %s: %s", event.id, account.provider, e)


def sync_pending(db: Session, user: User) -> int:
    """Выгружает события, которых ещё нет во включённых календарях. Возвращает число выгрузок."""
    accounts = sync_accounts(user)
    if not accounts:
        return 0
    done = 0
    events = db.scalars(select(Event).where(Event.user_id == user.id)).all()
    for account in accounts:
        for event in events:
            rec = _sync_record(event, account)
            if rec and rec.status == "synced":
                continue
            _sync_to(db, user, event, account)
            done += _sync_record(event, account).status == "synced"  # type: ignore[union-attr]
            if account.calendar_status == "error":
                break  # календарь недоступен — не долбим провайдера на каждом событии
    db.commit()
    return done


def setup_calendars_in_background(user_id: uuid.UUID) -> None:
    """После входа/подключения: создаёт календари и выгружает несинхронизированные события."""
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user:
            sync_pending(db, user)
            invalidate_busy_cache(user.id)


def sync_status(event: Event, user: User) -> str | None:
    """Сводный статус выгрузки события: synced | pending | error; None — выгружать некуда."""
    enabled = {a.id for a in sync_accounts(user)}
    if not enabled:
        return None
    recs = [s for s in event.syncs if s.account_id in enabled]
    if any(s.status == "error" for s in recs):
        return "error"
    if len(recs) == len(enabled) and all(s.status == "synced" for s in recs):
        return "synced"
    return "pending"


def list_events(db: Session, user: User, start: datetime, end: datetime) -> list[Event]:
    return list(
        db.scalars(
            select(Event).where(Event.user_id == user.id, Event.start >= start, Event.start < end).order_by(Event.start)
        )
    )


def external_events(db: Session, user: User, start: datetime, end: datetime) -> list[ExternalEvent]:
    """События из остальных календарей всех подключённых аккаунтов (только чтение). Ошибки — пропускаем."""
    key = (user.id, start, end)
    cached = _busy_cache.get(key)
    if cached and time.monotonic() - cached[0] < BUSY_CACHE_TTL:
        return cached[1]
    out: list[ExternalEvent] = []
    for account in user.accounts:
        backend = backend_for(db, user, account)
        if not backend:
            continue
        try:
            found = backend.external_events(start, end, account.calendar_id)
        except CalendarError as e:
            log.info("Не удалось прочитать календарь %s: %s", account.provider, e)
            continue
        for x in found:
            x.source = account.provider
        out.extend(x for x in found if start <= as_utc(x.start) < end)
    _busy_cache[key] = (time.monotonic(), out)
    return out


def invalidate_busy_cache(user_id: uuid.UUID) -> None:
    for key in [k for k in _busy_cache if k[0] == user_id]:
        _busy_cache.pop(key, None)
