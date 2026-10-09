from __future__ import annotations

import asyncio
import json
import math
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from benchmarks.renters.renters_benchmark.core import canonical
from .config import ModelSettings


@dataclass(frozen=True)
class Completion:
    raw: dict[str, Any]
    content: str | None
    message: dict[str, Any] | None = None


@dataclass(frozen=True)
class ToolTurn:
    message: dict[str, Any]


def validate_tool_message(message: dict[str, Any]) -> None:
    calls = message.get("tool_calls")
    if (not isinstance(calls, list) or not calls or len(calls) > 32
            or message.get("content") is not None and not isinstance(message["content"], str)):
        raise ValueError("Invalid tool-call message")
    ids = set()
    for call in calls:
        if (not isinstance(call, dict) or not isinstance(call.get("id"), str) or not call["id"]
                or call["id"] in ids or call.get("type") != "function"
                or not isinstance(call.get("function"), dict)
                or not isinstance(call["function"].get("name"), str)
                or not call["function"]["name"]
                or not isinstance(call["function"].get("arguments"), str)):
            raise ValueError("Invalid or duplicate tool call")
        ids.add(call["id"])


class ProviderError(Exception):
    def __init__(self, message: str, raw: Any = None):
        super().__init__(message)
        self.raw = raw


class Client(Protocol):
    async def complete(self, role: str, settings: ModelSettings,
                       messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None,
                       tool_choice: str = "auto") -> Completion: ...


def request_body(settings: ModelSettings, messages: list[dict[str, Any]], *,
                 tools: list[dict[str, Any]] | None = None, tool_choice: str = "auto") -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": settings.model,
        "messages": messages,
        "temperature": settings.temperature,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    if settings.max_tokens is not None:
        body["max_tokens"] = settings.max_tokens
    if tools is not None:
        body.update(tools=tools, tool_choice=tool_choice)
        # Allow native tool calls; request JSON-object output for the final-only turn.
        if tool_choice != "none":
            body.pop("response_format")
    return body


class OpenRouterClient:
    def __init__(self, timeout_seconds: int = 120):
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key.strip():
            raise ValueError("Set OPENROUTER_API_KEY in the environment before a live run")
        self.timeout = timeout_seconds

    async def complete(self, role: str, settings: ModelSettings,
                       messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None,
                       tool_choice: str = "auto") -> Completion:
        return await asyncio.to_thread(self._send, settings, messages, tools, tool_choice)

    def _send(self, settings: ModelSettings, messages: list[dict[str, Any]],
              tools: list[dict[str, Any]] | None = None, tool_choice: str = "auto") -> Completion:
        request = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=canonical(request_body(settings, messages, tools=tools, tool_choice=tool_choice)).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = parse_object(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Do not persist HTTP headers or credentials.
            raise ProviderError(f"OpenRouter HTTP {exc.code}", exc.read().decode(errors="replace")) from exc
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise ProviderError(f"OpenRouter transport/JSON failure: {type(exc).__name__}") from exc
        if not isinstance(raw, dict) or raw.get("error"):
            raise ProviderError("OpenRouter error envelope", raw)
        try:
            choice = raw["choices"][0]
            message = choice["message"]
            if not isinstance(message, dict):
                raise ValueError("Invalid completion message")
            content = message.get("content")
            if choice.get("finish_reason") == "tool_calls" and tools is not None and tool_choice != "none":
                validate_tool_message(message)
            elif (choice.get("finish_reason") != "stop" or message.get("tool_calls")
                  or not isinstance(content, str) or not content.strip()):
                raise ValueError("Incomplete completion")
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("OpenRouter missing or incomplete completion", raw) from exc
        return Completion(raw, content, message)


def parse_object(content: str) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"Duplicate key: {key}")
            value[key] = item
        return value

    def reject(value: str) -> None:
        raise ValueError(f"Non-finite JSON: {value}")

    def finite_float(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite JSON number")
        return number

    result = json.loads(content, object_pairs_hook=unique, parse_constant=reject, parse_float=finite_float)
    if not isinstance(result, dict):
        raise ValueError("Completion must be a JSON object")
    return result
