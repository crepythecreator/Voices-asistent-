import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import as_utc, get_db
from ..models import ChatMessage, ProposedAction, User
from ..security import current_user
from . import actions
from .agent import resolve_timezone, run_agent
from .gigachat import get_llm

router = APIRouter(tags=["assistant"])


class ActionOut(BaseModel):
    id: str
    type: str
    summary: str
    status: str
    error: str | None
    eventId: str | None
    expiresAt: datetime


class MessageOut(BaseModel):
    id: str
    role: str
    text: str
    source: str | None
    createdAt: datetime
    actions: list[ActionOut] = []


def action_out(a: ProposedAction) -> ActionOut:
    return ActionOut(
        id=str(a.id),
        type=a.type,
        summary=a.summary,
        status=a.status,
        error=a.error,
        eventId=str(a.event_id) if a.event_id else None,
        expiresAt=as_utc(a.expires_at),
    )


def message_out(m: ChatMessage, acts: list[ProposedAction] | None = None) -> MessageOut:
    return MessageOut(
        id=str(m.id),
        role=m.role,
        text=m.text,
        source=m.source,
        createdAt=as_utc(m.created_at),
        actions=[action_out(a) for a in (acts if acts is not None else m.actions)],
    )


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    source: Literal["text", "voice"] = "text"
    timezone: str | None = None


class ChatOut(BaseModel):
    reply: str
    message: MessageOut


@router.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> ChatOut:
    tz = resolve_timezone(body.timezone, user.timezone)
    if tz.key != user.timezone:
        user.timezone = tz.key
    reply, proposed = run_agent(db, user, get_llm(), body.message.strip(), body.source, tz)
    return ChatOut(reply=reply.text, message=message_out(reply, proposed))


@router.get("/chat/history", response_model=list[MessageOut])
def history(limit: int = 50, user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[MessageOut]:
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id)
        .options(selectinload(ChatMessage.actions))
        .order_by(ChatMessage.created_at.desc())
        .limit(min(limit, 200))
    ).all()
    return [message_out(m) for m in reversed(rows)]


def _resolve(fn, action_id: uuid.UUID, user: User, db: Session) -> ActionOut:
    try:
        return action_out(fn(db, user, action_id))
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except actions.ActionStateError as e:
        raise HTTPException(409, str(e)) from e


@router.post("/actions/{action_id}/confirm", response_model=ActionOut)
def confirm_action(action_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> ActionOut:
    """Единственный путь, которым ИИ-предложение попадает в календарь."""
    return _resolve(actions.apply_action, action_id, user, db)


@router.post("/actions/{action_id}/reject", response_model=ActionOut)
def reject_action(action_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> ActionOut:
    return _resolve(actions.reject_action, action_id, user, db)
