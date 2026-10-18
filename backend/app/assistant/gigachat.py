"""Клиент GigaChat REST API: https://developers.sber.ru/docs/ru/gigachat/api/overview

Пишем на httpx, а не через SDK: SDK часто меняет интерфейс, а нам нужны два запроса.
"""

import json
import logging
import ssl
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import certifi
import httpx

from ..config import settings
from .llm import FunctionCall, LLMError, LLMReply

log = logging.getLogger(__name__)

# Токен живёт 30 минут — обновляем чуть раньше
TOKEN_REFRESH_MARGIN = 60


def _ssl_context() -> ssl.SSLContext | bool:
    if not settings.gigachat_verify_ssl:
        return False
    ctx = ssl.create_default_context(cafile=certifi.where())
    ca = settings.gigachat_ca_file
    if ca and Path(ca).exists():
        ctx.load_verify_locations(cafile=ca)
    return ctx


class GigaChatClient:
    def __init__(self) -> None:
        if not settings.gigachat_credentials:
            raise LLMError("Не задан GIGACHAT_CREDENTIALS")
        self._http = httpx.Client(verify=_ssl_context(), timeout=60)
        self._token: str | None = None
        self._token_expires = 0.0
        self._lock = threading.Lock()

    def _access_token(self) -> str:
        with self._lock:
            if self._token and time.time() < self._token_expires - TOKEN_REFRESH_MARGIN:
                return self._token
            try:
                resp = self._http.post(
                    settings.gigachat_auth_url,
                    headers={
                        "Authorization": f"Basic {settings.gigachat_credentials}",
                        "RqUID": str(uuid.uuid4()),
                        "Accept": "application/json",
                    },
                    data={"scope": settings.gigachat_scope},
                )
            except httpx.HTTPError as e:
                raise LLMError(f"GigaChat недоступен: {e}") from e
            if resp.status_code != 200:
                raise LLMError(f"GigaChat: ошибка авторизации {resp.status_code}: {resp.text[:300]}")
            body = resp.json()
            self._token = body["access_token"]
            self._token_expires = body["expires_at"] / 1000  # миллисекунды
            return self._token

    def chat(self, messages: list[dict[str, Any]], functions: list[dict[str, Any]]) -> LLMReply:
        payload: dict[str, Any] = {
            "model": settings.gigachat_model,
            "messages": messages,
            "temperature": 0.2,
        }
        if functions:
            payload["functions"] = functions
            payload["function_call"] = "auto"
        try:
            resp = self._http.post(
                f"{settings.gigachat_api_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self._access_token()}"},
                json=payload,
            )
        except httpx.HTTPError as e:
            raise LLMError(f"GigaChat недоступен: {e}") from e
        if resp.status_code == 401:
            self._token = None  # токен отозван — получим новый при следующем запросе
        if resp.status_code != 200:
            raise LLMError(f"GigaChat: {resp.status_code}: {resp.text[:300]}")

        message = resp.json()["choices"][0]["message"]
        call = message.get("function_call")
        function_call = None
        if call:
            args = call.get("arguments") or {}
            if isinstance(args, str):  # на всякий случай: иногда аргументы приходят строкой
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            function_call = FunctionCall(name=call["name"], arguments=args)
        extra = {"functions_state_id": message["functions_state_id"]} if message.get("functions_state_id") else {}
        return LLMReply(content=message.get("content") or "", function_call=function_call, extra=extra)


_client: GigaChatClient | None = None


def get_llm() -> GigaChatClient | None:
    """Клиент-синглтон (кеширует токен). None — GigaChat не настроен."""
    global _client
    if _client is None and settings.gigachat_credentials:
        _client = GigaChatClient()
    return _client
