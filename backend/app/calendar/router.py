from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import as_utc, get_db
from ..models import Event, User
from ..security import current_user
from . import service

router = APIRouter(tags=["calendar"])

MAX_RANGE_DAYS = 100


class EventOut(BaseModel):
    id: str
    title: str
    kind: Literal["meeting", "reminder", "task"]
    start: datetime
    end: datetime | None
    description: str | None = None
    # assistant — наше событие; yandex — из других календарей Яндекса, только чтение
    source: Literal["assistant", "yandex"] = "assistant"
    readonly: bool = False
    syncStatus: str | None = None
    calendarName: str | None = None


def event_out(e: Event) -> EventOut:
    return EventOut(
        id=str(e.id),
        title=e.title,
        kind=e.kind,  # type: ignore[arg-type]
        start=as_utc(e.start),
        end=as_utc(e.end) if e.end else None,
        description=e.description,
        syncStatus=e.sync_status,
    )


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.get("/events", response_model=list[EventOut])
def get_events(
    start: datetime = Query(alias="from"),
    end: datetime = Query(alias="to"),
    include_yandex: bool = True,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[EventOut]:
    start, end = _aware(start), _aware(end)
    if end <= start or (end - start).days > MAX_RANGE_DAYS:
        raise HTTPException(422, f"Некорректный диапазон (не больше {MAX_RANGE_DAYS} дней)")

    out = [event_out(e) for e in service.list_events(db, user, start, end)]
    if include_yandex:
        for x in service.external_events(db, user, start, end):
            out.append(
                EventOut(
                    id=f"yandex:{x.uid}:{x.start.isoformat()}",
                    title=x.title,
                    kind="meeting",
                    start=x.start,
                    end=x.end,
                    source="yandex",
                    readonly=True,
                    calendarName=x.calendar_name,
                )
            )
    out.sort(key=lambda e: e.start)
    return out


class CalendarStatusOut(BaseModel):
    connected: bool
    dedicated: bool
    status: str
    error: str | None
    unsynced: int


@router.get("/calendar/status", response_model=CalendarStatusOut)
def calendar_status(user: User = Depends(current_user), db: Session = Depends(get_db)) -> CalendarStatusOut:
    link = user.calendar
    unsynced = db.scalar(
        select(func.count()).select_from(Event).where(Event.user_id == user.id, Event.sync_status != "synced")
    )
    return CalendarStatusOut(
        connected=bool(link and link.status == "ok"),
        dedicated=bool(link and link.dedicated),
        status=link.status if link else "pending",
        error=link.error if link else None,
        unsynced=unsynced or 0,
    )


@router.post("/calendar/sync", response_model=CalendarStatusOut)
def calendar_sync(user: User = Depends(current_user), db: Session = Depends(get_db)) -> CalendarStatusOut:
    """Повторная выгрузка событий, которые не удалось отправить в Яндекс."""
    if user.calendar and user.calendar.status == "error":
        user.calendar.status = "pending"  # дать ensure_calendar попробовать заново
    service.sync_pending(db, user)
    service.invalidate_busy_cache(user.id)
    return calendar_status(user, db)
