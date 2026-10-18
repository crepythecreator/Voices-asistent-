"""Абстракция LLM: агенту неважно, какой провайдер под капотом."""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class FunctionCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMReply:
    content: str
    function_call: FunctionCall | None = None
    # Служебные поля провайдера, которые нужно вернуть в истории вместе с ответом
    extra: dict[str, Any] = field(default_factory=dict)


class LLMError(Exception):
    pass


class LLMClient(Protocol):
    def chat(self, messages: list[dict[str, Any]], functions: list[dict[str, Any]]) -> LLMReply: ...
