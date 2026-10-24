"""Предложенные ИИ изменения календаря.

Модель не меняет календарь напрямую: её «изменяющие» функции создают ProposedAction, а применяет
его apply_action — с повторной проверкой (не просрочено, событие существует и принадлежит пользователю).

Кто вызывает apply_action, зависит от режима пользователя (users.confirm_mode):
- confirm — только пользователь, кнопкой или голосом (POST /actions/{id}/confirm);
- auto — сервер сразу после предложения, кроме удаления: оно необратимо и всегда ждёт подтверждения.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..calendar import service as calendar
from ..db import as_utc, utcnow
from ..models import Event, ProposedAction, User

ACTION_TTL = timedelta(hours=24)
CONFIRM_MODES = ("confirm", "auto")
# Что в режиме auto применяется без подтверждения. Удаление — никогда: его не отменить, а текст
# из чужих календарей (названия событий) мог бы подтолкнуть модель удалить лишнее.
AUTO_APPLY_TYPES = {"create_event", "update_event"}
ActionType = Literal["create_event", "update_event", "delete_event"]
EventKind = Literal["meeting", "reminder", "task"]

KIND_NAMES = {"meeting": "встречу", "reminder": "напоминание", "task": "задачу"}
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]


class ActionValidationError(Exception):
    """Некорректные аргументы от модели. Текст уходит модели, чтобы она исправилась."""


class ActionStateError(Exception):
    """Действие нельзя применить/отклонить в текущем состоянии."""


def needs_confirmation(user: User, action_type: str) -> bool:
    return user.confirm_mode != "auto" or action_type not in AUTO_APPLY_TYPES


# --- Разбор аргументов от модели ---------------------------------------------------------


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


class CreateArgs(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    kind: EventKind = "meeting"
    start: str
    end: str | None = None
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("title", "description", mode="before")
    @classmethod
    def strip_text(cls, v: Any) -> Any:
        return _clean(v) if isinstance(v, str) else v


class UpdateArgs(BaseModel):
    event_id: str
    title: str | None = Field(default=None, min_length=1, max_length=200)
    kind: EventKind | None = None
    start: str | None = None
    end: str | None = None
    description: str | None = Field(default=None, max_length=2000)


class DeleteArgs(BaseModel):
    event_id: str


def parse_datetime(value: str, tz: ZoneInfo) -> datetime:
    """ISO 8601 от модели. Время без часового пояса считаем временем пользователя."""
    try:
        dt = datetime.fromisoformat(value.strip())
    except (ValueError, AttributeError) as e:
        raise ActionValidationError(f"Неверный формат даты «{value}», нужен ISO 8601, например 2026-10-20T15:00") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(timezone.utc)


def _validate(model: type[BaseModel], args: dict[str, Any]) -> Any:
    try:
        return model.model_validate(args)
    except ValidationError as e:
        problems = "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors())
        raise ActionValidationError(f"Неверные аргументы: {problems}") from e


def _check_range(start: datetime, end: datetime | None) -> None:
    if end is not None and end <= start:
        raise ActionValidationError("Конец события должен быть позже начала")
    if start < utcnow() - timedelta(days=1):
        raise ActionValidationError("Нельзя планировать событие в прошлом")
    if start > utcnow() + timedelta(days=5 * 365):
        raise ActionValidationError("Дата слишком далеко в будущем")


def find_user_event(db: Session, user: User, event_id: str) -> Event:
    try:
        eid = uuid.UUID(str(event_id))
    except ValueError as e:
        raise ActionValidationError(f"Событие {event_id} не найдено. Сначала вызови list_events.") from e
    event = db.get(Event, eid)
    if not event or event.user_id != user.id:
        raise ActionValidationError(f"Событие {event_id} не найдено. Сначала вызови list_events.")
    return event


# --- Человекочитаемое описание ------------------------------------------------------------


def format_when(start: datetime, end: datetime | None, tz: ZoneInfo) -> str:
    s = as_utc(start).astimezone(tz)
    text = f"{s.day} {MONTHS[s.month - 1]}, {s:%H:%M}"
    if end:
        e = as_utc(end).astimezone(tz)
        text += f"–{e:%H:%M}" if e.date() == s.date() else f" – {e.day} {MONTHS[e.month - 1]}, {e:%H:%M}"
    return text


def _iso(dt: datetime | None) -> str | None:
    return as_utc(dt).isoformat() if dt else None


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


# --- Предложение -------------------------------------------------------------------------


def propose(db: Session, user: User, action_type: str, args: dict[str, Any], tz: ZoneInfo) -> ProposedAction:
    """Проверяет аргументы и сохраняет черновик действия. Календарь НЕ меняется."""
    if action_type == "create_event":
        a = _validate(CreateArgs, args)
        start = parse_datetime(a.start, tz)
        end = parse_datetime(a.end, tz) if a.end else None
        _check_range(start, end)
        payload = {"title": a.title, "kind": a.kind, "start": _iso(start), "end": _iso(end), "description": a.description}
        summary = f"Создать {KIND_NAMES[a.kind]} «{a.title}» — {format_when(start, end, tz)}"
        event_id = None

    elif action_type == "update_event":
        a = _validate(UpdateArgs, args)
        event = find_user_event(db, user, a.event_id)
        changes: dict[str, Any] = {}
        if a.title and a.title != event.title:
            changes["title"] = a.title
        if a.kind and a.kind != event.kind:
            changes["kind"] = a.kind
        if a.description is not None and a.description != (event.description or ""):
            changes["description"] = a.description
        new_start = parse_datetime(a.start, tz) if a.start else as_utc(event.start)
        new_end = parse_datetime(a.end, tz) if a.end else (as_utc(event.end) if event.end else None)
        if a.start and not a.end and event.end:
            new_end = new_start + (as_utc(event.end) - as_utc(event.start))  # сохраняем длительность
        if new_start != as_utc(event.start):
            changes["start"] = _iso(new_start)
        if new_end != (as_utc(event.end) if event.end else None):
            changes["end"] = _iso(new_end)
        if not changes:
            raise ActionValidationError("Изменений нет: новые значения совпадают с текущими")
        _check_range(new_start, new_end)
        payload = {"event_id": str(event.id), "changes": changes}
        parts = []
        if "title" in changes:
            parts.append(f"название → «{changes['title']}»")
        if "start" in changes or "end" in changes:
            parts.append(f"время → {format_when(new_start, new_end, tz)}")
        if "kind" in changes:
            parts.append(f"тип → {KIND_NAMES[changes['kind']]}")
        if "description" in changes:
            parts.append("описание")
        summary = f"Изменить «{event.title}»: " + ", ".join(parts)
        event_id = event.id

    elif action_type == "delete_event":
        a = _validate(DeleteArgs, args)
        event = find_user_event(db, user, a.event_id)
        payload = {"event_id": str(event.id)}
        summary = f"Удалить «{event.title}» — {format_when(event.start, event.end, tz)}"
        event_id = event.id

    else:
        raise ActionValidationError(f"Неизвестное действие {action_type}")

    action = ProposedAction(
        user_id=user.id,
        type=action_type,
        payload=payload,
        summary=summary,
        event_id=event_id,
        expires_at=utcnow() + ACTION_TTL,
    )
    db.add(action)
    db.flush()
    return action


# --- Применение (только по подтверждению пользователя) ------------------------------------


def _load_pending(db: Session, user: User, action_id: uuid.UUID) -> ProposedAction:
    action = db.scalar(
        select(ProposedAction)
        .where(ProposedAction.id == action_id, ProposedAction.user_id == user.id)
        .with_for_update()  # двойное нажатие «Подтвердить» не применит действие дважды
    )
    if not action:
        raise LookupError("Действие не найдено")
    if action.status != "pending":
        raise ActionStateError(f"Действие уже в статусе {action.status}")
    if as_utc(action.expires_at) <= utcnow():
        action.status, action.resolved_at = "expired", utcnow()
        db.commit()
        raise ActionStateError("Срок подтверждения истёк, попросите ассистента ещё раз")
    return action


def apply_action(db: Session, user: User, action_id: uuid.UUID) -> ProposedAction:
    action = _load_pending(db, user, action_id)
    p = action.payload
    try:
        if action.type == "create_event":
            start, end = _dt(p["start"]), _dt(p.get("end"))
            _check_range(start, end)  # type: ignore[arg-type]
            new_id = uuid.uuid4()
            event = Event(
                id=new_id,
                user_id=user.id,
                title=p["title"],
                kind=p["kind"],
                start=start,
                end=end,
                description=p.get("description"),
                ical_uid=f"{new_id}@voice-assistant",
            )
            db.add(event)
            db.flush()
            calendar.sync_event(db, user, event)
            action.event_id = event.id

        elif action.type == "update_event":
            event = find_user_event(db, user, p["event_id"])
            changes = p["changes"]
            for field in ("title", "kind", "description"):
                if field in changes:
                    setattr(event, field, changes[field])
            if "start" in changes:
                event.start = _dt(changes["start"])  # type: ignore[assignment]
            if "end" in changes:
                event.end = _dt(changes["end"])
            if event.end and as_utc(event.end) <= as_utc(event.start):
                raise ActionValidationError("Конец события должен быть позже начала")
            calendar.sync_event(db, user, event)

        elif action.type == "delete_event":
            event = find_user_event(db, user, p["event_id"])
            calendar.unsync_event(db, user, event)
            db.delete(event)

        action.status = "applied"
    except ActionValidationError as e:
        # Например, событие удалили, пока действие ждало подтверждения
        db.rollback()
        action = db.get(ProposedAction, action_id)  # type: ignore[assignment]
        action.status, action.error = "failed", str(e)
    action.resolved_at = utcnow()
    db.commit()
    return action


def reject_action(db: Session, user: User, action_id: uuid.UUID) -> ProposedAction:
    action = _load_pending(db, user, action_id)
    action.status, action.resolved_at = "rejected", utcnow()
    db.commit()
    return action
