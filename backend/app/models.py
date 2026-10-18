import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    yandex_id: Mapped[str] = mapped_column(String(64), unique=True)
    login: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255))
    avatar_id: Mapped[str | None] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    token: Mapped["YandexToken | None"] = relationship(back_populates="user", cascade="all, delete-orphan")
    calendar: Mapped["CalendarLink | None"] = relationship(back_populates="user", cascade="all, delete-orphan")


class YandexToken(Base):
    """OAuth-токены Яндекса. Хранятся только в зашифрованном виде (см. security.encrypt)."""

    __tablename__ = "yandex_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    access_token_enc: Mapped[str] = mapped_column(Text)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scope: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="token")


class AuthSession(Base):
    """Сессия браузера. В БД — только sha256 от значения cookie."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()


class CalendarLink(Base):
    """Календарь пользователя в Яндексе, куда выгружаем наши события."""

    __tablename__ = "calendar_links"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    calendar_url: Mapped[str | None] = mapped_column(Text)
    # true — отдельный календарь, созданный нами; false — пишем в основной (не удалось создать)
    dedicated: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | ok | error
    error: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="calendar")


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
    sync_status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | synced | error | disabled
    sync_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


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
