"""Google Calendar API v3: https://developers.google.com/workspace/calendar/api/v3/reference

Права: calendar.app.created — свой календарь и события в нём; calendarlist.readonly и
events.readonly — только чтение остальных календарей для занятости.
"""

import logging
from datetime import date, datetime, time, timezone
from typing import Any
from urllib.parse import quote

import httpx

from ..db import as_utc
from ..models import Event
from .backend import CalendarError
from .ical import ExternalEvent, event_end

log = logging.getLogger(__name__)

API = "https://www.googleapis.com/calendar/v3"


def _parse_time(value: dict[str, str] | None) -> datetime | None:
    if not value:
        return None
    if "dateTime" in value:
        return datetime.fromisoformat(value["dateTime"].replace("Z", "+00:00")).astimezone(timezone.utc)
    if "date" in value:  # событие на весь день
        return datetime.combine(date.fromisoformat(value["date"]), time.min, tzinfo=timezone.utc)
    return None


class GoogleCalendarClient:
    def __init__(self, access_token: str, timezone_name: str):
        self._http = httpx.Client(base_url=API, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
        self._tz = timezone_name

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            resp = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as e:
            raise CalendarError(f"Google Calendar недоступен: {e}") from e
        if resp.status_code == 401:
            raise CalendarError("Нет доступа к Google Календарю: токен недействителен")
        return resp

    @staticmethod
    def _error(resp: httpx.Response, what: str) -> CalendarError:
        try:
            message = resp.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = resp.text[:200]
        return CalendarError(f"{what}: {resp.status_code} {message}")

    def ensure_calendar(self, name: str, known_id: str | None) -> str:
        if known_id:
            resp = self._request("GET", f"/calendars/{quote(known_id, safe='')}")
            if resp.status_code == 200:
                return known_id
            if resp.status_code not in (404, 410):
                raise self._error(resp, "Не удалось проверить календарь")
        resp = self._request("POST", "/calendars", json={"summary": name, "timeZone": self._tz})
        if resp.status_code != 200:
            raise self._error(resp, "Не удалось создать календарь")
        return resp.json()["id"]

    def _body(self, event: Event) -> dict[str, Any]:
        body: dict[str, Any] = {
            "summary": event.title,
            "description": event.description or "",
            "start": {"dateTime": as_utc(event.start).isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": event_end(event).isoformat(), "timeZone": "UTC"},
            "extendedProperties": {"private": {"voicesEventId": str(event.id), "kind": event.kind}},
        }
        if event.kind == "reminder":
            body["reminders"] = {"useDefault": False, "overrides": [{"method": "popup", "minutes": 0}]}
        return body

    def upsert_event(self, calendar_id: str, event: Event, remote_id: str | None) -> str:
        cal = quote(calendar_id, safe="")
        if remote_id:
            resp = self._request("PUT", f"/calendars/{cal}/events/{quote(remote_id, safe='')}", json=self._body(event))
            if resp.status_code == 200:
                return remote_id
            if resp.status_code not in (404, 410):
                raise self._error(resp, "Не удалось обновить событие")
            # Событие удалили в Google — создаём заново
        resp = self._request("POST", f"/calendars/{cal}/events", json=self._body(event))
        if resp.status_code != 200:
            raise self._error(resp, "Не удалось создать событие")
        return resp.json()["id"]

    def delete_event(self, calendar_id: str, remote_id: str) -> None:
        resp = self._request("DELETE", f"/calendars/{quote(calendar_id, safe='')}/events/{quote(remote_id, safe='')}")
        if resp.status_code not in (200, 204, 404, 410):
            raise self._error(resp, "Не удалось удалить событие")

    def external_events(self, start: datetime, end: datetime, exclude_id: str | None) -> list[ExternalEvent]:
        resp = self._request("GET", "/users/me/calendarList", params={"minAccessRole": "reader"})
        if resp.status_code == 403:
            return []  # пользователь не выдал право на список календарей
        if resp.status_code != 200:
            raise self._error(resp, "Не удалось получить список календарей")

        out: list[ExternalEvent] = []
        for cal in resp.json().get("items", []):
            if cal["id"] == exclude_id or cal.get("hidden") or not cal.get("selected", True):
                continue
            events = self._request(
                "GET",
                f"/calendars/{quote(cal['id'], safe='')}/events",
                params={
                    "timeMin": as_utc(start).isoformat(),
                    "timeMax": as_utc(end).isoformat(),
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 250,
                },
            )
            if events.status_code != 200:
                log.info("Пропускаем календарь Google %s: %s", cal["id"], events.status_code)
                continue
            for item in events.json().get("items", []):
                ev_start = _parse_time(item.get("start"))
                if item.get("status") == "cancelled" or not ev_start:
                    continue
                out.append(
                    ExternalEvent(
                        uid=item["id"],
                        title=item.get("summary") or "Занято",
                        start=ev_start,
                        end=_parse_time(item.get("end")),
                        calendar_name=cal.get("summaryOverride") or cal.get("summary") or "Google Календарь",
                        source="google",
                    )
                )
        return out
