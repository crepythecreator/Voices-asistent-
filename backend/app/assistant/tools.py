"""Функции, доступные модели.

list_events — только чтение. propose_* — только создают черновик действия (см. actions.py):
модель физически не может изменить календарь, даже если её «уговорят» текстом в событии.
"""

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..calendar import service as calendar
from ..db import as_utc
from ..models import ProposedAction, User
from . import actions
from .actions import ActionValidationError

log = logging.getLogger(__name__)

MAX_LIST_DAYS = 62

_EVENT_FIELDS = {
    "title": {"type": "string", "description": "Короткое название, например «Позвонить врачу»"},
    "kind": {
        "type": "string",
        "enum": ["meeting", "reminder", "task"],
        "description": "meeting — встреча, reminder — напоминание, task — задача",
    },
    "start": {"type": "string", "description": "Начало, локальное время пользователя в ISO 8601: 2026-10-20T15:00"},
    "end": {"type": "string", "description": "Конец в том же формате. Необязательно"},
    "description": {"type": "string", "description": "Подробности. Необязательно"},
}

_PROPOSAL_RESULT = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["proposed", "error"]},
        "summary": {"type": "string", "description": "Что именно предложено"},
        "error": {"type": "string", "description": "Почему предложение не принято — исправь аргументы"},
    },
}

FUNCTIONS: list[dict[str, Any]] = [
    {
        "name": "list_events",
        "description": (
            "Возвращает события пользователя за период. source=assistant — события ассистента, их можно "
            "предлагать изменить или удалить по id. source=yandex — события из других календарей Яндекса, "
            "только для понимания занятости, менять их нельзя."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "from": {"type": "string", "description": "Начало периода, ISO 8601: 2026-10-20T00:00"},
                "to": {"type": "string", "description": "Конец периода, ISO 8601: 2026-10-21T00:00"},
            },
            "required": ["from", "to"],
        },
        "few_shot_examples": [
            {"request": "Что у меня завтра?", "params": {"from": "2026-10-20T00:00", "to": "2026-10-21T00:00"}}
        ],
        "return_parameters": {
            "type": "object",
            "properties": {
                "events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Только у событий ассистента"},
                            "source": {"type": "string", "enum": ["assistant", "yandex"]},
                            "title": {"type": "string"},
                            "kind": {"type": "string"},
                            "start": {"type": "string"},
                            "end": {"type": "string"},
                        },
                    },
                }
            },
        },
    },
    {
        "name": "propose_create_event",
        "description": (
            "Предлагает создать встречу, напоминание или задачу. Событие НЕ создаётся: пользователь "
            "увидит карточку и подтвердит её сам."
        ),
        "parameters": {"type": "object", "properties": _EVENT_FIELDS, "required": ["title", "kind", "start"]},
        "few_shot_examples": [
            {
                "request": "Напомни завтра в 9 утра позвонить врачу",
                "params": {"title": "Позвонить врачу", "kind": "reminder", "start": "2026-10-20T09:00"},
            },
            {
                "request": "Встреча с Олегом в среду с 15 до 16",
                "params": {
                    "title": "Встреча с Олегом",
                    "kind": "meeting",
                    "start": "2026-10-21T15:00",
                    "end": "2026-10-21T16:00",
                },
            },
        ],
        "return_parameters": _PROPOSAL_RESULT,
    },
    {
        "name": "propose_update_event",
        "description": (
            "Предлагает изменить событие ассистента (source=assistant). Передай event_id из list_events и "
            "только меняющиеся поля. Изменение НЕ выполняется до подтверждения пользователем."
        ),
        "parameters": {
            "type": "object",
            "properties": {"event_id": {"type": "string", "description": "id из list_events"}, **_EVENT_FIELDS},
            "required": ["event_id"],
        },
        "return_parameters": _PROPOSAL_RESULT,
    },
    {
        "name": "propose_delete_event",
        "description": (
            "Предлагает удалить событие ассистента (source=assistant) по event_id из list_events. "
            "Удаление НЕ выполняется до подтверждения пользователем."
        ),
        "parameters": {
            "type": "object",
            "properties": {"event_id": {"type": "string", "description": "id из list_events"}},
            "required": ["event_id"],
        },
        "return_parameters": _PROPOSAL_RESULT,
    },
]

PROPOSAL_FUNCTIONS = {
    "propose_create_event": "create_event",
    "propose_update_event": "update_event",
    "propose_delete_event": "delete_event",
}


@dataclass
class ToolContext:
    db: Session
    user: User
    tz: ZoneInfo
    proposed: list[ProposedAction] = field(default_factory=list)


def _local(dt, tz: ZoneInfo) -> str | None:
    return as_utc(dt).astimezone(tz).strftime("%Y-%m-%dT%H:%M") if dt else None


def _list_events(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    start = actions.parse_datetime(str(args.get("from", "")), ctx.tz)
    end = actions.parse_datetime(str(args.get("to", "")), ctx.tz)
    if end <= start:
        raise ActionValidationError("Конец периода должен быть позже начала")
    end = min(end, start + timedelta(days=MAX_LIST_DAYS))

    events = [
        {
            "id": str(e.id),
            "source": "assistant",
            "title": e.title,
            "kind": e.kind,
            "start": _local(e.start, ctx.tz),
            "end": _local(e.end, ctx.tz),
        }
        for e in calendar.list_events(ctx.db, ctx.user, start, end)
    ]
    events += [
        {"source": "yandex", "title": x.title, "start": _local(x.start, ctx.tz), "end": _local(x.end, ctx.tz)}
        for x in calendar.external_events(ctx.db, ctx.user, start, end)
    ]
    events.sort(key=lambda e: e["start"] or "")
    return {"events": events}


def execute(ctx: ToolContext, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Выполняет функцию модели. Ошибки возвращаются модели текстом, чтобы она могла исправиться."""
    try:
        if name == "list_events":
            return _list_events(ctx, args)
        if name in PROPOSAL_FUNCTIONS:
            action = actions.propose(ctx.db, ctx.user, PROPOSAL_FUNCTIONS[name], args, ctx.tz)
            ctx.proposed.append(action)
            return {
                "status": "proposed",
                "summary": action.summary,
                "note": "Изменение НЕ выполнено. Пользователь подтвердит или отклонит его в карточке под ответом.",
            }
        return {"status": "error", "error": f"Неизвестная функция {name}"}
    except ActionValidationError as e:
        return {"status": "error", "error": str(e)}
