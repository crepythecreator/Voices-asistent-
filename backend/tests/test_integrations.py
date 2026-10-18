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
