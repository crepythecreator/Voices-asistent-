"""Преобразование наших событий в iCalendar и обратно."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from icalendar import Alarm, Calendar
from icalendar import Event as IEvent

from ..db import as_utc, utcnow
from ..models import Event

KIND_LABELS = {"meeting": "Встреча", "reminder": "Напоминание", "task": "Задача"}

# Если конец не указан, событие в Яндексе всё равно должно иметь длительность
DEFAULT_DURATION = {"meeting": timedelta(hours=1), "reminder": timedelta(minutes=15), "task": timedelta(minutes=30)}


def event_end(event: Event) -> datetime:
    return as_utc(event.end) if event.end else as_utc(event.start) + DEFAULT_DURATION.get(event.kind, timedelta(minutes=30))


def to_ical(event: Event) -> str:
    cal = Calendar()
    cal.add("prodid", "-//Voice Assistant//RU")
    cal.add("version", "2.0")

    ev = IEvent()
    ev.add("uid", event.ical_uid)
    ev.add("dtstamp", utcnow())
    ev.add("summary", event.title)
    ev.add("dtstart", as_utc(event.start))
    ev.add("dtend", event_end(event))
    ev.add("categories", [KIND_LABELS.get(event.kind, event.kind)])
    if event.description:
        ev.add("description", event.description)
    if event.kind == "reminder":
        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", event.title)
        alarm.add("trigger", timedelta(0))
        ev.add_component(alarm)

    cal.add_component(ev)
    return cal.to_ical().decode()


@dataclass
class ExternalEvent:
    uid: str
    title: str
    start: datetime
    end: datetime | None
    calendar_name: str
    # yandex | google — откуда событие
    source: str = "yandex"


def _as_datetime(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    # Событие на весь день
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def parse_external(ical_text: str, calendar_name: str) -> list[ExternalEvent]:
    out = []
    for comp in Calendar.from_ical(ical_text).walk("VEVENT"):
        start = comp.get("dtstart")
        if not start:
            continue
        end = comp.get("dtend")
        out.append(
            ExternalEvent(
                uid=str(comp.get("uid", "")),
                title=str(comp.get("summary", "Занято")),
                start=_as_datetime(start.dt),
                end=_as_datetime(end.dt) if end else None,
                calendar_name=calendar_name,
            )
        )
    return out
