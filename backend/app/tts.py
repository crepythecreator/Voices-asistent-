"""Синтез речи: GigaChat/SaluteSpeech через Realtime API Cloud.ru (WebSocket).

Отправляем текст событием response.create, собираем куски PCM из response.output_audio.delta
до response.done и отдаём фронту WAV (16 бит, моно, 24 кГц).
"""

import base64
import io
import json
import logging
import re
import wave

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from websocket import WebSocketException, create_connection

from .config import settings
from .models import User
from .security import current_user

log = logging.getLogger(__name__)

SAMPLE_RATE = 24000
MAX_TEXT_LENGTH = 1000  # фронт присылает ответ по предложениям — этого с запасом

router = APIRouter()


class TtsError(Exception):
    pass


def clean_for_speech(text: str) -> str:
    """Убирает разметку, которую синтез зачитал бы вслух («звёздочка», «решётка»)."""
    text = re.sub(r"[*_`#>]+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # [текст](ссылка) → текст
    return re.sub(r"\s+", " ", text).strip()


def synthesize_pcm(text: str, voice: str | None = None) -> bytes:
    """Синтезирует речь и возвращает сырой PCM 16 бит, моно, 24 кГц."""
    try:
        ws = create_connection(
            settings.tts_url,
            header=[f"Authorization: Bearer {settings.cloudru_api_key}"],
            suppress_origin=True,
            timeout=60,
        )
    except (WebSocketException, OSError) as e:
        raise TtsError(f"Сервис синтеза недоступен: {e}") from e

    audio = bytearray()
    try:
        ws.send(
            json.dumps(
                {
                    "type": "response.create",
                    "model": settings.tts_model,
                    "response": {
                        "output_modalities": ["audio"],
                        "audio": {
                            "output": {
                                "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                                "voice": voice or settings.tts_voice,
                                "speed": settings.tts_speed,
                            }
                        },
                        "input": [
                            {"type": "message", "role": "user", "content": [{"type": "input_text", "text": text}]}
                        ],
                    },
                }
            )
        )
        while True:
            message = ws.recv()
            if not message:
                raise TtsError("Соединение закрыто до завершения синтеза")
            event = json.loads(message)
            kind = event.get("type")
            if kind == "response.output_audio.delta":
                audio.extend(base64.b64decode(event["delta"]))
            elif kind == "error":
                raise TtsError(f"Ошибка синтеза: {event.get('error', event)}")
            elif kind == "response.done":
                status = event.get("response", {}).get("status")
                if status in {"failed", "cancelled", "incomplete"}:
                    raise TtsError(f"Синтез не завершён: {status}")
                break
    except (WebSocketException, OSError, ValueError) as e:
        raise TtsError(f"Ошибка соединения с сервисом синтеза: {e}") from e
    finally:
        ws.close()

    if not audio:
        raise TtsError("Сервис синтеза не вернул аудио")
    return bytes(audio)


def to_wav(pcm: bytes, rate: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm)
    return buf.getvalue()


class TtsIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)


@router.post("/tts", response_class=Response, responses={200: {"content": {"audio/wav": {}}}})
def text_to_speech(body: TtsIn, _user: User = Depends(current_user)) -> Response:
    """Озвучивает текст. Синтез платный — только для вошедших."""
    if not settings.cloudru_api_key:
        raise HTTPException(503, "Не задан CLOUDRU_API_KEY — синтез речи недоступен")
    text = clean_for_speech(body.text)
    if not text:
        raise HTTPException(422, "Нечего озвучивать")
    try:
        pcm = synthesize_pcm(text)
    except TtsError as e:
        log.warning("TTS: %s", e)
        raise HTTPException(502, str(e)) from e
    return Response(content=to_wav(pcm), media_type="audio/wav", headers={"Cache-Control": "no-store"})
