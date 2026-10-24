from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
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
    # assistant — событие ассистента; yandex/google — из других календарей, только чтение
    source: Literal["assistant", "yandex", "google"] = "assistant"
    readonly: bool = False
    # synced | pending | error; None — нет календарей с включённой синхронизацией
    syncStatus: str | None = None
    calendarName: str | None = None
    # Событие на весь день — время не показываем
    allDay: bool = False


def event_out(e: Event, user: User) -> EventOut:
    return EventOut(
        id=str(e.id),
        title=e.title,
        kind=e.kind,  # type: ignore[arg-type]
        start=as_utc(e.start),
        end=as_utc(e.end) if e.end else None,
        description=e.description,
        syncStatus=service.sync_status(e, user),
    )


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.get("/events", response_model=list[EventOut])
def get_events(
    start: datetime = Query(alias="from"),
    end: datetime = Query(alias="to"),
    include_external: bool = True,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[EventOut]:
    start, end = _aware(start), _aware(end)
    if end <= start or (end - start).days > MAX_RANGE_DAYS:
        raise HTTPException(422, f"Некорректный диапазон (не больше {MAX_RANGE_DAYS} дней)")

    out = [event_out(e, user) for e in service.list_events(db, user, start, end)]
    if include_external:
        for x in service.external_events(db, user, start, end):
            out.append(
                EventOut(
                    id=f"{x.source}:{x.uid}:{x.start.isoformat()}",
                    title=x.title,
                    kind="meeting",
                    start=x.start,
                    end=x.end,
                    source=x.source,  # type: ignore[arg-type]
                    readonly=True,
                    calendarName=x.calendar_name,
                    allDay=x.all_day,
                )
            )
    out.sort(key=lambda e: e.start)
    return out


@router.post("/calendar/sync", status_code=204)
def calendar_sync(user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    """Повторная выгрузка событий, которые не удалось отправить в календари."""
    for account in service.sync_accounts(user):
        if account.calendar_status == "error":
            account.calendar_status = "pending"  # дать ещё одну попытку
    service.sync_pending(db, user)
    service.invalidate_busy_cache(user.id)
