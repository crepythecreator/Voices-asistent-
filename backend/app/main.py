import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import stt, tts
from .account.router import router as account_router
from .assistant.router import router as assistant_router
from .auth.router import router as auth_router
from .calendar.router import router as calendar_router
from .config import settings

logging.basicConfig(level=logging.INFO)
if settings.app_secret_key in ("", "dev-secret-change-me"):
    logging.getLogger(__name__).warning("APP_SECRET_KEY не задан — используется небезопасный ключ для разработки")

app = FastAPI(title="Voice Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(account_router)
app.include_router(assistant_router)
app.include_router(calendar_router)
app.include_router(stt.router)
app.include_router(tts.router)


@app.get("/health")
def health():
    return {"status": "ok"}
