"""Распознавание речи через Yandex SpeechKit (синхронное API v1).

Фронт присылает сырой PCM: 16 бит, little-endian, моно. Ограничения SpeechKit:
не больше 30 секунд и 1 МБ на запрос.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from .config import settings
from .models import User
from .security import current_user

SPEECHKIT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
MAX_BYTES = 1024 * 1024

router = APIRouter()


class SttResponse(BaseModel):
    text: str


@router.post("/stt", response_model=SttResponse)
async def speech_to_text(
    request: Request,
    sample_rate: int = Query(16000),
    lang: str = Query("ru-RU"),
    _user: User = Depends(current_user),  # распознавание платное — только для вошедших
) -> SttResponse:
    if not settings.yandex_api_key:
        raise HTTPException(503, "Не задан YANDEX_API_KEY — серверное распознавание недоступно")
    if sample_rate not in (8000, 16000, 48000):
        raise HTTPException(422, "sample_rate должен быть 8000, 16000 или 48000")

    audio = await request.body()
    if not audio:
        raise HTTPException(422, "Пустое аудио")
    if len(audio) > MAX_BYTES:
        raise HTTPException(413, "Запись слишком длинная (максимум ~30 секунд)")

    params = {"lang": lang, "format": "lpcm", "sampleRateHertz": sample_rate}
    if settings.yandex_folder_id:
        params["folderId"] = settings.yandex_folder_id

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                SPEECHKIT_URL,
                params=params,
                content=audio,
                headers={"Authorization": f"Api-Key {settings.yandex_api_key}"},
            )
    except httpx.HTTPError as e:
        raise HTTPException(502, f"SpeechKit недоступен: {e}") from e

    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if resp.status_code != 200:
        raise HTTPException(502, f"SpeechKit: {data.get('error_message') or resp.text}")

    return SttResponse(text=data.get("result", ""))
