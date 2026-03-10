"""Vendor-agnostic LLM client abstraction.

Provides a Protocol-based interface so agent code works with any LLM provider.
Provider is selected via QF_LLM_PROVIDER env var (default: openai).

Usage:
    client = get_client()  # reads QF_LLM_PROVIDER from env
    response = client.complete(
        system="You are a helpful assistant.",
        messages=[{"role": "user", "content": "Hello"}],
    )
"""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Vendor-agnostic LLM interface.

    All agent code should depend on this Protocol, never on a concrete client.
    """

    def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """Send a completion request and return the assistant's text response.

        Args:
            system: System prompt (e.g., router.txt content).
            messages: Conversation messages in [{"role": ..., "content": ...}] format.
            **kwargs: Provider-specific options (model, temperature, max_tokens, etc.).

        Returns:
            The assistant's response text.
        """
        ...


class OpenAIClient:
    """OpenAI / ChatGPT Team implementation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
    ):
        try:
            import openai
        except ImportError as exc:
            raise ImportError("openai package required: pip install openai") from exc

        self._client = openai.OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self._default_model = model

    def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        model = kwargs.pop("model", self._default_model)
        full_messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        full_messages.extend(messages)

        response = self._client.chat.completions.create(
            model=model,
            messages=full_messages,
            **kwargs,
        )
        return response.choices[0].message.content or ""


class AnthropicClient:
    """Anthropic / Claude implementation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
    ):
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError("anthropic package required: pip install anthropic") from exc

        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self._default_model = model

    def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        model = kwargs.pop("model", self._default_model)
        max_tokens = kwargs.pop("max_tokens", 4096)

        response = self._client.messages.create(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.content[0].text


_PROVIDERS: dict[str, type] = {
    "openai": OpenAIClient,
    "anthropic": AnthropicClient,
}


def get_client(provider: str | None = None, **kwargs: Any) -> LLMClient:
    """Factory - create an LLM client for the configured provider.

    Args:
        provider: "openai" or "anthropic". Defaults to QF_LLM_PROVIDER env var
                  (fallback: "openai").
        **kwargs: Passed to the client constructor (api_key, model, etc.).

    Returns:
        An LLMClient instance.
    """
    provider = provider or os.environ.get("QF_LLM_PROVIDER", "openai")
    provider = provider.lower()

    if provider not in _PROVIDERS:
        available = ", ".join(sorted(_PROVIDERS))
        raise ValueError(f"Unknown LLM provider '{provider}'. Available: {available}")

    return _PROVIDERS[provider](**kwargs)
