"""Пароли (argon2) и ограничение попыток входа."""

import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from ..config import settings

MIN_PASSWORD_LENGTH = 8

_hasher = PasswordHasher()
# Хеш-заглушка: проверяем пароль, даже если пользователя нет, — чтобы время ответа не выдавало, есть ли почта
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def normalize_email(email: str | None) -> str | None:
    return email.strip().lower() if email else None


class LoginRateLimiter:
    """Неудачные попытки входа в памяти процесса: по почте и по IP."""

    def __init__(self) -> None:
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _recent(self, key: str) -> deque[float]:
        window = settings.login_window_minutes * 60
        q = self._failures[key]
        while q and time.monotonic() - q[0] > window:
            q.popleft()
        return q

    def blocked(self, *keys: str) -> bool:
        return any(len(self._recent(k)) >= settings.login_max_attempts for k in keys)

    def fail(self, *keys: str) -> None:
        for k in keys:
            self._recent(k).append(time.monotonic())

    def reset(self, *keys: str) -> None:
        for k in keys:
            self._failures.pop(k, None)


login_limiter = LoginRateLimiter()
