import json
from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.db import SessionLocal, utcnow
from app.models import Event, ProposedAction

from .conftest import ScriptedLLM, call, login, text

TOMORROW = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


def events_count() -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(Event)) or 0


def chat(client, message: str) -> dict:
    r = client.post("/chat", json={"message": message, "timezone": "Europe/Moscow"})
    assert r.status_code == 200, r.text
    return r.json()


def propose_create(llm_use, client, title="Позвонить врачу"):
    llm_use(
        ScriptedLLM(
            call("propose_create_event", title=title, kind="reminder", start=f"{TOMORROW}T09:00"),
            text("Подготовил напоминание — подтвердите его."),
        )
    )
    return chat(client, f"Напомни завтра в 9 {title.lower()}")


def test_ai_only_proposes_and_does_not_touch_calendar(user_client, use_llm, calendars):
    body = propose_create(use_llm, user_client)

    actions = body["message"]["actions"]
    assert len(actions) == 1
    assert actions[0]["status"] == "pending"
    assert "Позвонить врачу" in actions[0]["summary"]
    # Ничего не создано ни у нас, ни в Яндексе
    assert events_count() == 0
    assert calendars["yandex"].saved == {}


def test_confirm_applies_and_syncs_to_yandex(user_client, use_llm, calendars):
    action_id = propose_create(use_llm, user_client)["message"]["actions"][0]["id"]

    r = user_client.post(f"/actions/{action_id}/confirm")
    assert r.status_code == 200
    assert r.json()["status"] == "applied"
    assert events_count() == 1
    assert list(calendars["yandex"].saved.values()) == ["Позвонить врачу"]
    assert calendars["google"].saved == {}  # Google не подключён

    # Повторное подтверждение не создаёт дубль
    assert user_client.post(f"/actions/{action_id}/confirm").status_code == 409
    assert events_count() == 1


def test_reject_leaves_calendar_untouched(user_client, use_llm, calendars):
    action_id = propose_create(use_llm, user_client)["message"]["actions"][0]["id"]
    r = user_client.post(f"/actions/{action_id}/reject")
    assert r.json()["status"] == "rejected"
    assert user_client.post(f"/actions/{action_id}/confirm").status_code == 409
    assert events_count() == 0


def test_expired_action_cannot_be_confirmed(user_client, use_llm, calendars):
    action_id = propose_create(use_llm, user_client)["message"]["actions"][0]["id"]
    with SessionLocal() as db:
        action = db.scalar(select(ProposedAction))
        action.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    assert user_client.post(f"/actions/{action_id}/confirm").status_code == 409
    assert events_count() == 0


def test_invalid_arguments_are_returned_to_model(user_client, use_llm, calendars):
    llm = use_llm(
        ScriptedLLM(
            call(
                "propose_create_event",
                title="Встреча",
                kind="meeting",
                start=f"{TOMORROW}T15:00",
                end=f"{TOMORROW}T14:00",
            ),
            text("Уточните, пожалуйста, время."),
        )
    )
    body = chat(user_client, "Встреча завтра с 15 до 14")
    assert body["message"]["actions"] == []
    function_result = json.loads(llm.requests[1][-1]["content"])
    assert function_result["status"] == "error"
    assert "позже начала" in function_result["error"]


def test_hallucinated_event_id_is_rejected(user_client, use_llm, calendars):
    llm = use_llm(
        ScriptedLLM(
            call("propose_delete_event", event_id="00000000-0000-0000-0000-000000000000"),
            text("Не нашёл такое событие."),
        )
    )
    body = chat(user_client, "Удали встречу")
    assert body["message"]["actions"] == []
    assert json.loads(llm.requests[1][-1]["content"])["status"] == "error"


def test_cannot_touch_other_users_events(client, use_llm, calendars, monkeypatch):
    # Первый пользователь создаёт событие
    login(client, monkeypatch, yandex_id="1")
    action_id = propose_create(use_llm, client)["message"]["actions"][0]["id"]
    client.post(f"/actions/{action_id}/confirm")
    with SessionLocal() as db:
        event_id = str(db.scalar(select(Event.id)))

    # Второй пытается удалить его через ИИ и напрямую подтвердить чужое действие
    login(client, monkeypatch, yandex_id="2")
    llm = use_llm(ScriptedLLM(call("propose_delete_event", event_id=event_id), text("Не нашёл.")))
    chat(client, "Удали событие")
    assert json.loads(llm.requests[1][-1]["content"])["status"] == "error"
    assert client.post(f"/actions/{action_id}/confirm").status_code == 404
    assert events_count() == 1


def test_update_and_delete_flow(user_client, use_llm, calendars):
    action_id = propose_create(use_llm, user_client)["message"]["actions"][0]["id"]
    user_client.post(f"/actions/{action_id}/confirm")
    with SessionLocal() as db:
        event = db.scalar(select(Event))

    use_llm(ScriptedLLM(call("propose_update_event", event_id=str(event.id), start=f"{TOMORROW}T10:30"), text("Ок")))
    update = chat(user_client, "Перенеси на 10:30")["message"]["actions"][0]
    assert "10:30" in update["summary"]
    with SessionLocal() as db:
        assert db.get(Event, event.id).start == event.start  # до подтверждения ничего не меняется
    user_client.post(f"/actions/{update['id']}/confirm")
    with SessionLocal() as db:
        assert db.get(Event, event.id).start != event.start

    use_llm(ScriptedLLM(call("propose_delete_event", event_id=str(event.id)), text("Ок")))
    delete = chat(user_client, "Удали его")["message"]["actions"][0]
    assert events_count() == 1
    user_client.post(f"/actions/{delete['id']}/confirm")
    assert events_count() == 0
    assert calendars["yandex"].deleted == [f"yandex-{event.id}"]


def test_list_events_includes_yandex_busy_as_readonly(user_client, use_llm, calendars):
    from app.calendar.ical import ExternalEvent
    from datetime import timezone

    start = datetime.now(timezone.utc) + timedelta(days=1)
    calendars["yandex"].external = [ExternalEvent("x1", "Работа", start, start + timedelta(hours=1), "Рабочий")]
    r = user_client.get(
        "/events",
        params={"from": (start - timedelta(days=1)).isoformat(), "to": (start + timedelta(days=1)).isoformat()},
    )
    assert r.status_code == 200
    [event] = r.json()
    assert event["source"] == "yandex" and event["readonly"] is True


def test_history_contains_actions(user_client, use_llm, calendars):
    propose_create(use_llm, user_client)
    history = user_client.get("/chat/history").json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[1]["actions"][0]["status"] == "pending"


def test_without_llm_configured(user_client):
    body = chat(user_client, "Привет")
    assert "GIGACHAT_CREDENTIALS" in body["reply"]


def test_sync_to_both_calendars_and_toggle(user_client, use_llm, calendars, monkeypatch):
    from .conftest import oauth

    # Подключаем ещё и Google — события ассистента уходят в оба календаря
    oauth(user_client, monkeypatch, "google", "connect", "/settings", user_id="g1")
    action_id = propose_create(use_llm, user_client)["message"]["actions"][0]["id"]
    user_client.post(f"/actions/{action_id}/confirm")
    assert len(calendars["yandex"].saved) == 1 and len(calendars["google"].saved) == 1

    # Синхронизация с Google выключена — новые события туда не идут
    user_client.patch("/account/connections/google", json={"syncEnabled": False})
    action_id = propose_create(use_llm, user_client, title="Купить хлеб")["message"]["actions"][0]["id"]
    user_client.post(f"/actions/{action_id}/confirm")
    assert len(calendars["yandex"].saved) == 2 and len(calendars["google"].saved) == 1


def test_sync_error_is_reported_and_retried(user_client, use_llm, calendars):
    calendars["yandex"].fail = True
    action_id = propose_create(use_llm, user_client)["message"]["actions"][0]["id"]
    assert user_client.post(f"/actions/{action_id}/confirm").json()["status"] == "applied"  # событие у нас создано

    with SessionLocal() as db:
        event = db.scalar(select(Event))
    start = event.start.replace(tzinfo=None)
    params = {"from": (start - timedelta(days=1)).isoformat() + "Z", "to": (start + timedelta(days=1)).isoformat() + "Z"}
    assert user_client.get("/events", params=params).json()[0]["syncStatus"] == "error"

    calendars["yandex"].fail = False
    assert user_client.post("/calendar/sync").status_code == 204
    assert user_client.get("/events", params=params).json()[0]["syncStatus"] == "synced"


def test_external_events_from_google(user_client, use_llm, calendars, monkeypatch):
    from datetime import timezone

    from app.calendar.ical import ExternalEvent

    from .conftest import oauth

    oauth(user_client, monkeypatch, "google", "connect", "/settings", user_id="g1")
    start = datetime.now(timezone.utc) + timedelta(days=1)
    calendars["google"].external = [ExternalEvent("g1", "Стоматолог", start, None, "Личный")]
    r = user_client.get(
        "/events", params={"from": (start - timedelta(hours=1)).isoformat(), "to": (start + timedelta(hours=1)).isoformat()}
    )
    [event] = r.json()
    assert event["source"] == "google" and event["readonly"] is True
