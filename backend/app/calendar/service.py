"""Наши события и их выгрузка в Яндекс Календарь.

Источник правды — наша БД. Яндекс получает копию событий в отдельном календаре;
ошибка синхронизации не откатывает изменение, а помечает событие (sync_status=error),
его можно выгрузить повторно через POST /calendar/sync.
"""

import logging
import time
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import yandex
from ..config import settings
from ..db import SessionLocal, as_utc
from ..models import CalendarLink, Event, User
from .ical import ExternalEvent, to_ical
from .yandex_caldav import CalendarError, YandexCalendarClient

log = logging.getLogger(__name__)

# Занятость из Яндекса кешируем ненадолго: CalDAV-запросы медленные
BUSY_CACHE_TTL = 60
_busy_cache: dict[tuple[uuid.UUID, datetime, datetime], tuple[float, list[ExternalEvent]]] = {}


def caldav_username(user: User) -> str:
    return user.email or f"{user.login}@yandex.ru"


def _client(db: Session, user: User) -> YandexCalendarClient | None:
    token = yandex.get_access_token(db, user)
    return YandexCalendarClient(caldav_username(user), token) if token else None


def ensure_calendar(db: Session, user: User, client: YandexCalendarClient) -> CalendarLink:
    link = user.calendar or CalendarLink(user_id=user.id)
    user.calendar = link
    if link.status == "ok" and link.calendar_url:
        return link
    try:
        link.calendar_url, link.dedicated = client.ensure_calendar(settings.yandex_calendar_name, link.calendar_url)
        link.status, link.error = "ok", None
    except CalendarError as e:
        link.status, link.error = "error", str(e)[:1000]
        db.commit()
        raise
    db.commit()
    return link


def setup_calendar_in_background(user_id: uuid.UUID) -> None:
    """Создаёт календарь сразу после входа и выгружает несинхронизированные события."""
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user:
            sync_pending(db, user)


def sync_event(db: Session, user: User, event: Event) -> None:
    client = _client(db, user)
    if not client:
        event.sync_status, event.sync_error = "disabled", "Нет доступа к Яндекс Календарю"
        return
    try:
        link = ensure_calendar(db, user, client)
        client.put_event(link.calendar_url, to_ical(event))  # type: ignore[arg-type]
        event.sync_status, event.sync_error = "synced", None
    except CalendarError as e:
        log.warning("Синхронизация события %s не удалась: %s", event.id, e)
        event.sync_status, event.sync_error = "error", str(e)[:1000]


def unsync_event(db: Session, user: User, event: Event) -> None:
    """Удаляет копию события из Яндекса. Ошибки только логируем — локально событие уже удалено."""
    if event.sync_status != "synced":
        return
    client = _client(db, user)
    link = user.calendar
    if not client or not link or not link.calendar_url:
        return
    try:
        client.delete_event(link.calendar_url, event.ical_uid)
    except CalendarError as e:
        log.warning("Не удалось удалить событие %s из Яндекса: %s", event.id, e)


def sync_pending(db: Session, user: User) -> int:
    """Выгружает события, которые ещё не попали в Яндекс. Возвращает число успешных."""
    client = _client(db, user)
    if not client:
        return 0
    try:
        ensure_calendar(db, user, client)
    except CalendarError:
        return 0
    events = db.scalars(
        select(Event).where(Event.user_id == user.id, Event.sync_status.in_(["pending", "error", "disabled"]))
    ).all()
    ok = 0
    for event in events:
        sync_event(db, user, event)
        ok += event.sync_status == "synced"
    db.commit()
    return ok


def list_events(db: Session, user: User, start: datetime, end: datetime) -> list[Event]:
    return list(
        db.scalars(
            select(Event).where(Event.user_id == user.id, Event.start >= start, Event.start < end).order_by(Event.start)
        )
    )


def external_events(db: Session, user: User, start: datetime, end: datetime) -> list[ExternalEvent]:
    """События из других календарей Яндекса (только чтение). При ошибке — пустой список."""
    key = (user.id, start, end)
    cached = _busy_cache.get(key)
    if cached and time.monotonic() - cached[0] < BUSY_CACHE_TTL:
        return cached[1]
    client = _client(db, user)
    if not client:
        return []
    exclude = user.calendar.calendar_url if user.calendar else None
    try:
        events = client.external_events(start, end, exclude)
    except CalendarError as e:
        log.info("Не удалось прочитать Яндекс Календарь: %s", e)
        return []
    events = [e for e in events if start <= as_utc(e.start) < end]
    _busy_cache[key] = (time.monotonic(), events)
    return events


def invalidate_busy_cache(user_id: uuid.UUID) -> None:
    for key in [k for k in _busy_cache if k[0] == user_id]:
        _busy_cache.pop(key, None)
