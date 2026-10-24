"""Распознавание речи на сервере. Нужно браузерам, у которых нет рабочего Web Speech API
(Яндекс Браузер, Brave, Arc, Firefox).

Фронт присылает сырой PCM: 16 бит, little-endian, моно. Провайдеры:
- cloudru — Cloud.ru Foundation Models, OpenAI-совместимый /audio/transcriptions
  (GigaChat/GigaASR по умолчанию, openai/whisper-large-v3 — запасной), тот же ключ, что и для синтеза речи;
- yandex — Yandex SpeechKit (синхронное API v1).
"""

import io
import wave

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from .config import settings
from .models import User
from .security import current_user

SPEECHKIT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
# 30 секунд PCM 16 кГц — ~960 КБ
MAX_BYTES = 1024 * 1024
SAMPLE_RATES = (8000, 16000, 24000, 44100, 48000)

router = APIRouter()


class SttResponse(BaseModel):
    text: str


class SttStatus(BaseModel):
    available: bool
    provider: str | None


def resolve_provider() -> str | None:
    """cloudru или yandex; None — серверное распознавание не настроено."""
    choice = settings.stt_provider
    if choice == "cloudru":
        return "cloudru" if settings.cloudru_api_key else None
    if choice == "yandex":
        return "yandex" if settings.yandex_api_key else None
    if settings.cloudru_api_key:
        return "cloudru"
    return "yandex" if settings.yandex_api_key else None


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=30)


def pcm_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(pcm)
    return buf.getvalue()


async def recognize_cloudru(audio: bytes, sample_rate: int, lang: str) -> str:
    models = [settings.stt_model, *(m for m in (settings.stt_fallback_model,) if m and m != settings.stt_model)]
    last_error = ""
    wav = pcm_to_wav(audio, sample_rate)
    for model in models:
        try:
            async with _client() as client:
                resp = await client.post(
                    f"{settings.cloudru_base_url.rstrip('/')}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.cloudru_api_key}"},
                    files={"file": ("speech.wav", wav, "audio/wav")},
                    data={"model": model, "language": lang.split("-")[0].lower()},
                )
        except httpx.HTTPError as e:
            last_error = f"сервис распознавания недоступен: {e}"
            continue
        if resp.status_code == 200:
            return str(resp.json().get("text", "")).strip()
        last_error = f"{model}: {resp.status_code} {resp.text[:200]}"
        if resp.status_code in (401, 403):
            break  # другая модель не поможет — проблема в ключе
    raise HTTPException(502, f"Распознавание: {last_error}")


async def recognize_yandex(audio: bytes, sample_rate: int, lang: str) -> str:
    if sample_rate not in (8000, 16000, 48000):
        raise HTTPException(422, "Для Yandex SpeechKit sample_rate должен быть 8000, 16000 или 48000")
    params = {"lang": lang, "format": "lpcm", "sampleRateHertz": sample_rate}
    if settings.yandex_folder_id:
        params["folderId"] = settings.yandex_folder_id
    try:
        async with _client() as client:
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
    return str(data.get("result", ""))


@router.get("/stt/status", response_model=SttStatus)
def stt_status(_user: User = Depends(current_user)) -> SttStatus:
    provider = resolve_provider()
    return SttStatus(available=provider is not None, provider=provider)


@router.post("/stt", response_model=SttResponse)
async def speech_to_text(
    request: Request,
    sample_rate: int = Query(16000),
    lang: str = Query("ru-RU"),
    _user: User = Depends(current_user),  # распознавание платное — только для вошедших
) -> SttResponse:
    provider = resolve_provider()
    if not provider:
        raise HTTPException(503, "Не задан CLOUDRU_API_KEY или YANDEX_API_KEY — серверное распознавание недоступно")
    if sample_rate not in SAMPLE_RATES:
        raise HTTPException(422, f"sample_rate должен быть одним из {SAMPLE_RATES}")

    audio = await request.body()
    if not audio:
        raise HTTPException(422, "Пустое аудио")
    if len(audio) > MAX_BYTES:
        raise HTTPException(413, "Запись слишком длинная (максимум ~30 секунд)")

    text = await (recognize_cloudru if provider == "cloudru" else recognize_yandex)(audio, sample_rate, lang)
    return SttResponse(text=text)
