"""Общий интерфейс календарей провайдеров (Яндекс по CalDAV, Google по REST API)."""

from datetime import datetime
from typing import Protocol

from ..models import Event
from .ical import ExternalEvent


class CalendarError(Exception):
    pass


class CalendarBackend(Protocol):
    def ensure_calendar(self, name: str, known_id: str | None) -> str:
        """Находит или создаёт отдельный календарь ассистента. Возвращает его id/URL."""
        ...

    def upsert_event(self, calendar_id: str, event: Event, remote_id: str | None) -> str:
        """Создаёт или обновляет событие. Возвращает id события у провайдера."""
        ...

    def delete_event(self, calendar_id: str, remote_id: str) -> None: ...

    def external_events(self, start: datetime, end: datetime, exclude_id: str | None) -> list[ExternalEvent]:
        """События из остальных календарей пользователя — только чтение, для занятости."""
        ...
