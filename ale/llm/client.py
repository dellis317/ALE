"""LLM client wrapper for ALE.

Provides a unified interface to the Anthropic API with cost tracking,
graceful fallback when no API key is configured, and streaming support.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import AsyncGenerator

import anthropic


# ---------------------------------------------------------------------------
# Pricing table (USD per 1 M tokens)
# ---------------------------------------------------------------------------

MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-3-5-20241022": {"input": 0.80, "output": 4.0},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
}

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

_NOT_CONFIGURED_MSG = "LLM not configured. Set ANTHROPIC_API_KEY."


# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------


@dataclass
class LLMResponse:
    """Structured response from an LLM call."""

    content: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    cost_estimate: float = 0.0


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class LLMClient:
    """Thin wrapper around the Anthropic Python SDK.

    Parameters
    ----------
    model : str
        Model identifier to use for completions.
    api_key : str | None
        Anthropic API key.  Falls back to the ``ANTHROPIC_API_KEY``
        environment variable when *None*.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._configured = bool(self.api_key)

        if self._configured:
            self._client = anthropic.Anthropic(api_key=self.api_key)
            self._async_client = anthropic.AsyncAnthropic(api_key=self.api_key)
        else:
            self._client = None  # type: ignore[assignment]
            self._async_client = None  # type: ignore[assignment]

    # -- properties ----------------------------------------------------------

    @property
    def configured(self) -> bool:
        """Return *True* if an API key is available."""
        return self._configured

    # -- cost helpers --------------------------------------------------------

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        pricing = MODEL_PRICING.get(self.model, MODEL_PRICING[DEFAULT_MODEL])
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    # -- synchronous completion ----------------------------------------------

    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """Send a completion request and return an :class:`LLMResponse`.

        When no API key is configured the method returns a stub response
        with a helpful message instead of raising.
        """
        if not self._configured:
            return LLMResponse(content=_NOT_CONFIGURED_MSG, model=self.model)

        messages = [{"role": "user", "content": prompt}]
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        start = time.monotonic()
        response = self._client.messages.create(**kwargs)
        latency_ms = int((time.monotonic() - start) * 1000)

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        content = response.content[0].text if response.content else ""

        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            latency_ms=latency_ms,
            cost_estimate=self._estimate_cost(input_tokens, output_tokens),
        )

    # -- async streaming completion ------------------------------------------

    async def stream_complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the LLM as an async generator.

        When not configured, yields the stub message and returns.
        """
        if not self._configured:
            yield _NOT_CONFIGURED_MSG
            return

        messages = [{"role": "user", "content": prompt}]
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        async with self._async_client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
