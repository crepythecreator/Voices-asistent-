import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Почта в нижнем регистре. Может отсутствовать, если провайдер её не отдал
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    # Подтверждена провайдером (Яндекс/Google). Регистрация по паролю почту не подтверждает
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    # confirm — изменения календаря от ИИ применяются после подтверждения пользователем;
    # auto — создание и изменение применяются сразу, удаление всё равно ждёт подтверждения
    confirm_mode: Mapped[str] = mapped_column(String(16), default="confirm", server_default="confirm")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    accounts: Mapped[list["OAuthAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="OAuthAccount.created_at"
    )

    def account(self, provider: str) -> "OAuthAccount | None":
        return next((a for a in self.accounts if a.provider == provider), None)


class OAuthAccount(Base):
    """Подключённый аккаунт Яндекса или Google: вход, токены и календарь.

    Токены хранятся только в зашифрованном виде (см. security.encrypt).
    """

    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_accounts_provider_user"),
        UniqueConstraint("user_id", "provider", name="uq_oauth_accounts_user_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(16))  # yandex | google
    provider_user_id: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    access_token_enc: Mapped[str] = mapped_column(Text)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scope: Mapped[str | None] = mapped_column(Text)
    # Пользователь выдал доступ к календарю
    calendar_access: Mapped[bool] = mapped_column(Boolean, default=False)
    # Пользователь включил выгрузку событий ассистента в этот календарь
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # Наш календарь у провайдера: URL в CalDAV (Яндекс) или calendarId (Google)
    calendar_id: Mapped[str | None] = mapped_column(Text)
    calendar_status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | ok | error
    calendar_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="accounts")


class AuthSession(Base):
    """Сессия браузера. В БД — только sha256 от значения cookie."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_user_start", "user_id", "start"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(16))  # meeting | reminder | task
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text)
    # UID события в iCalendar — по нему находим событие в Яндекс Календаре
    ical_uid: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    syncs: Mapped[list["EventSync"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class EventSync(Base):
    """Копия события в календаре конкретного подключённого аккаунта."""

    __tablename__ = "event_syncs"

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("oauth_accounts.id", ondelete="CASCADE"), primary_key=True)
    # id события у провайдера: UID в CalDAV (Яндекс) или eventId (Google)
    remote_id: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | synced | error
    error: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    event: Mapped[Event] = relationship(back_populates="syncs")
    account: Mapped[OAuthAccount] = relationship()


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(16))  # text | voice
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    actions: Mapped[list["ProposedAction"]] = relationship(back_populates="message", order_by="ProposedAction.created_at")


class ProposedAction(Base):
    """Изменение календаря, предложенное ИИ. Применяется только после подтверждения пользователем."""

    __tablename__ = "proposed_actions"
    __table_args__ = (Index("ix_proposed_actions_user_status", "user_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chat_messages.id", ondelete="SET NULL"))
    type: Mapped[str] = mapped_column(String(32))  # create_event | update_event | delete_event
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | applied | rejected | expired | failed
    error: Mapped[str | None] = mapped_column(Text)
    event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    message: Mapped[ChatMessage | None] = relationship(back_populates="actions")
