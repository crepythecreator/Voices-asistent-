"""Яндекс Календарь по CalDAV (caldav.yandex.ru) с OAuth-токеном пользователя.

Публичного REST API у Яндекс Календаря нет; CalDAV с OAuth-токеном описан в справке Яндекс 360.
Логин — email пользователя, пароль — OAuth-токен.
"""

import logging
from datetime import datetime

import caldav
from caldav.lib.error import DAVError, NotFoundError

from ..config import settings
from .ical import ExternalEvent, parse_external

log = logging.getLogger(__name__)


class CalendarError(Exception):
    pass


class YandexCalendarClient:
    def __init__(self, username: str, access_token: str):
        self._client = caldav.DAVClient(url=settings.caldav_url, username=username, password=access_token, timeout=20)
        self._principal: caldav.Principal | None = None

    @property
    def principal(self) -> caldav.Principal:
        if self._principal is None:
            try:
                self._principal = self._client.principal()
            except DAVError as e:
                raise CalendarError(f"Нет доступа к Яндекс Календарю: {e}") from e
        return self._principal

    def calendars(self) -> list[caldav.Calendar]:
        return self.principal.calendars()

    def ensure_calendar(self, name: str, known_url: str | None) -> tuple[str, bool]:
        """Возвращает (url календаря, отдельный ли это календарь).

        Ищем наш календарь по сохранённому адресу или имени; если его нет — создаём (MKCALENDAR).
        Если сервер не дал создать календарь — откатываемся на основной календарь пользователя.
        """
        calendars = self.calendars()
        urls = {str(c.url) for c in calendars}
        if known_url and known_url in urls:
            return known_url, True
        for cal in calendars:
            if cal.name == name:
                return str(cal.url), True
        try:
            self.principal.make_calendar(name=name, supported_calendar_component_set=["VEVENT"])
            # Яндекс сам выбирает адрес нового календаря (events-<id>) и называет его по имени
            # OAuth-приложения — адрес из ответа caldav неверный, ищем новый календарь в списке.
            created = [c for c in self.calendars() if str(c.url) not in urls and "/events-" in str(c.url)]
            if created:
                return str(created[0].url), True
            log.warning("Календарь создан, но не найден в списке — пишем в основной")
        except DAVError as e:
            log.warning("Не удалось создать отдельный календарь, пишем в основной: %s", e)
        events_calendars = [c for c in calendars if "/events-" in str(c.url)]
        if not events_calendars:
            raise CalendarError("У пользователя нет календаря для событий")
        default = next((c for c in events_calendars if "events-default" in str(c.url)), events_calendars[0])
        return str(default.url), False

    def _calendar(self, url: str) -> caldav.Calendar:
        return caldav.Calendar(client=self._client, url=url)

    def put_event(self, calendar_url: str, ical: str) -> None:
        """Создаёт или перезаписывает событие (адрес определяется по UID)."""
        try:
            self._calendar(calendar_url).save_event(ical)
        except DAVError as e:
            raise CalendarError(f"Не удалось сохранить событие: {e}") from e

    def delete_event(self, calendar_url: str, uid: str) -> None:
        try:
            self._calendar(calendar_url).event_by_uid(uid).delete()
        except NotFoundError:
            pass  # уже удалено в Яндексе — нас это устраивает
        except DAVError as e:
            raise CalendarError(f"Не удалось удалить событие: {e}") from e

    def external_events(self, start: datetime, end: datetime, exclude_url: str | None) -> list[ExternalEvent]:
        """События из остальных календарей пользователя — только чтение, для занятости."""
        out: list[ExternalEvent] = []
        for cal in self.calendars():
            if exclude_url and str(cal.url) == exclude_url:
                continue
            try:
                found = cal.search(start=start, end=end, event=True, expand=True)
            except DAVError as e:
                log.info("Пропускаем календарь %s: %s", cal.url, e)
                continue
            for obj in found:
                out.extend(parse_external(obj.data, cal.name or "Яндекс Календарь"))
        return out
