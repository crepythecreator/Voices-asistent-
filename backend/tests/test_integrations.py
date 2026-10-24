import json
import time

import httpx

from app.assistant import gigachat
from app.calendar.ical import parse_external
from app.config import settings


def test_gigachat_client_auth_and_function_call(monkeypatch):
    monkeypatch.setattr(settings, "gigachat_credentials", "base64key")
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/oauth"):
            return httpx.Response(200, json={"access_token": "tok", "expires_at": int((time.time() + 1800) * 1000)})
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "function_call": {"name": "list_events", "arguments": {"from": "a", "to": "b"}},
                            "functions_state_id": "state-1",
                        },
                        "finish_reason": "function_call",
                    }
                ]
            },
        )

    client = gigachat.GigaChatClient()
    client._http = httpx.Client(transport=httpx.MockTransport(handler))
    reply = client.chat([{"role": "user", "content": "что завтра"}], [{"name": "list_events"}])
    client.chat([{"role": "user", "content": "ещё раз"}], [])

    auth, chat, chat2 = seen
    assert auth.headers["Authorization"] == "Basic base64key"
    assert auth.headers["RqUID"]
    assert b"scope=GIGACHAT_API_PERS" in auth.content
    assert chat.headers["Authorization"] == "Bearer tok"
    body = json.loads(chat.content)
    assert body["function_call"] == "auto" and body["functions"][0]["name"] == "list_events"
    assert "functions" not in json.loads(chat2.content)  # токен переиспользуется, без функций — без function_call
    assert reply.function_call.name == "list_events"
    assert reply.function_call.arguments == {"from": "a", "to": "b"}
    assert reply.extra == {"functions_state_id": "state-1"}


def test_parse_external_ical():
    ical = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Yandex//RU\r\n"
        "BEGIN:VEVENT\r\nUID:abc\r\nSUMMARY:Планёрка\r\nDTSTART:20261020T070000Z\r\nDTEND:20261020T080000Z\r\nEND:VEVENT\r\n"
        "BEGIN:VEVENT\r\nUID:day\r\nSUMMARY:Отпуск\r\nDTSTART;VALUE=DATE:20261021\r\nEND:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    events = parse_external(ical, "Рабочий")
    assert [e.title for e in events] == ["Планёрка", "Отпуск"]
    assert events[0].start.hour == 7 and events[0].start.tzinfo is not None
    assert events[1].start.tzinfo is not None  # событие на весь день


def test_google_calendar_client():
    import uuid
    from datetime import datetime, timedelta, timezone

    from app.calendar.google_calendar import GoogleCalendarClient
    from app.models import Event

    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path
        if request.method == "GET" and path.endswith("/calendars/old-id"):
            return httpx.Response(404, json={"error": {"message": "Not Found"}})
        if request.method == "POST" and path.endswith("/calendars"):
            return httpx.Response(200, json={"id": "voices@group.calendar.google.com"})
        if request.method == "POST" and path.endswith("/events"):
            return httpx.Response(200, json={"id": "ev1"})
        if path.endswith("/calendarList"):
            return httpx.Response(200, json={"items": [{"id": "voices@group.calendar.google.com"}, {"id": "primary-id", "summary": "Личный"}]})
        if path.endswith("/calendars/primary-id/events"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {"id": "a", "summary": "Стоматолог", "start": {"dateTime": "2026-10-24T10:00:00+03:00"}, "end": {"dateTime": "2026-10-24T11:00:00+03:00"}},
                        {"id": "b", "summary": "Отпуск", "start": {"date": "2026-10-25"}},
                        {"id": "c", "status": "cancelled", "start": {"date": "2026-10-26"}},
                    ]
                },
            )
        return httpx.Response(500)

    client = GoogleCalendarClient("tok", "Europe/Moscow")
    client._http = httpx.Client(base_url="https://www.googleapis.com/calendar/v3", transport=httpx.MockTransport(handler))

    # Сохранённый календарь удалили — создаём новый
    cal_id = client.ensure_calendar("Voices", "old-id")
    assert cal_id == "voices@group.calendar.google.com"
    assert json.loads(seen[-1].content) == {"summary": "Voices", "timeZone": "Europe/Moscow"}

    start = datetime(2026, 10, 24, 9, 0, tzinfo=timezone.utc)
    event = Event(id=uuid.uuid4(), title="Позвонить", kind="reminder", start=start, end=None, ical_uid="x")
    assert client.upsert_event(cal_id, event, None) == "ev1"
    body = json.loads(seen[-1].content)
    assert body["summary"] == "Позвонить" and body["start"]["dateTime"].startswith("2026-10-24T09:00")
    assert body["reminders"]["overrides"] == [{"method": "popup", "minutes": 0}]

    found = client.external_events(start, start + timedelta(days=3), exclude_id=cal_id)
    assert [e.title for e in found] == ["Стоматолог", "Отпуск"]  # свой календарь и отменённые пропущены
    assert found[0].start.hour == 7 and found[0].calendar_name == "Личный"


class FakeWebSocket:
    """Подмена WebSocket Realtime API: отдаёт два куска аудио и response.done."""

    def __init__(self, events):
        self.sent: list[dict] = []
        self.events = [json.dumps(e) for e in events]
        self.closed = False

    def send(self, data):
        self.sent.append(json.loads(data))

    def recv(self):
        return self.events.pop(0)

    def close(self):
        self.closed = True


def test_tts_endpoint_returns_wav(user_client, monkeypatch):
    import base64
    import io
    import wave

    from app import tts

    pcm = b"\x01\x00" * 2400  # 0,1 с тишины
    ws = FakeWebSocket(
        [
            {"type": "response.output_audio.delta", "delta": base64.b64encode(pcm[:2400]).decode()},
            {"type": "response.output_audio.delta", "delta": base64.b64encode(pcm[2400:]).decode()},
            {"type": "response.done", "response": {"status": "completed"}},
        ]
    )
    monkeypatch.setattr(settings, "cloudru_api_key", "key")
    monkeypatch.setattr(tts, "create_connection", lambda url, **kw: ws)

    r = user_client.post("/tts", json={"text": "**Готово!** Напоминание создано."})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"
    with wave.open(io.BytesIO(r.content)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (24000, 1, 2)
        assert w.readframes(w.getnframes()) == pcm
    request = ws.sent[0]
    assert request["model"] == "GigaChat/SaluteSpeech"
    assert request["response"]["input"][0]["content"][0]["text"] == "Готово! Напоминание создано."  # без разметки
    assert ws.closed


def test_tts_errors(user_client, monkeypatch):
    from app import tts

    assert user_client.post("/tts", json={"text": "привет"}).status_code == 503  # ключ не задан

    monkeypatch.setattr(settings, "cloudru_api_key", "key")
    ws = FakeWebSocket([{"type": "error", "error": {"message": "invalid voice"}}])
    monkeypatch.setattr(tts, "create_connection", lambda url, **kw: ws)
    r = user_client.post("/tts", json={"text": "привет"})
    assert r.status_code == 502 and "invalid voice" in r.json()["detail"]


def test_tts_requires_login(client):
    assert client.post("/tts", json={"text": "привет"}).status_code == 401
