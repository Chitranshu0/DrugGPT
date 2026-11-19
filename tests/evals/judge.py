"""OpenRouter chat clients shared by the eval judge, synthesizer, and harness.

The primary key is always the app's existing ``OPENROUTER_API_KEY`` with the
free ``DRUGGPT_EVAL_MODEL`` (default ``google/gemma-4-31b-it:free``). A second
key in ``OPENROUTER_FALLBACK_API_KEY`` is attached as a LangChain fallback and
is only used when the primary call fails. Nothing overwrites the primary key.
"""

from __future__ import annotations

import json
import time

from src.core.config import Settings
from src.core.runtime import configure_runtime

configure_runtime()

from deepeval.models import DeepEvalBaseLLM  # noqa: E402
from langchain_openrouter import ChatOpenRouter  # noqa: E402


def _client(model: str, api_key: str, max_tokens: int, temperature: float) -> ChatOpenRouter:
    # Fail fast on 429/5xx so LangChain's `with_fallbacks` can switch keys
    # instead of waiting out the OpenRouter SDK's own long retry backoff.
    return ChatOpenRouter(
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        # The SDK otherwise retries 429s with hour-long backoff, which prevents
        # LangChain's `with_fallbacks` from ever switching to the second key.
        model_kwargs={"retries": None, "timeout_ms": 10000},
    )


def build_fallback_client(max_tokens: int, temperature: float = 0.0) -> ChatOpenRouter | None:
    """Build the secondary OpenRouter key client, if configured."""
    settings = Settings()
    if not settings.eval_fallback_api_key:
        return None
    return _client(settings.eval_fallback_model, settings.eval_fallback_api_key, max_tokens, temperature)


def build_chat_model(max_tokens: int, temperature: float = 0.0):
    """Build the primary client with the secondary key attached as a fallback."""
    settings = Settings()
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY must be configured to run evals.")
    primary = _client(settings.eval_model, settings.openrouter_api_key, max_tokens, temperature)
    fallback = build_fallback_client(max_tokens, temperature)
    return primary.with_fallbacks([fallback]) if fallback is not None else primary


class EvalJudge(DeepEvalBaseLLM):
    """DeepEval judge with primary/fallback switching and empty-content retries."""

    def __init__(self, temperature: float = 0.0) -> None:
        self._temperature = temperature
        self._client = build_chat_model(4096, temperature)
        self._fallback = build_fallback_client(4096, temperature)
        super().__init__()

    def load_model(self):
        return self._client

    def get_model_name(self) -> str:
        return Settings().eval_model

    @staticmethod
    def _prepare(prompt: str, kwargs: dict) -> str:
        # DeepEval's synthesizer requests structured output via `schema=`.
        # The chat client cannot enforce a schema, so ask for plain JSON with
        # exactly the fields the schema declares, then parse it in _parse.
        schema = kwargs.get("schema")
        if schema is not None:
            fields = ", ".join(getattr(schema, "model_fields", {}).keys())
            return (
                f"{prompt}\nRespond with a single JSON object with exactly these keys: {fields}. "
                "No markdown and no other text."
            )
        return prompt

    @staticmethod
    def _parse(text: str, schema):
        if schema is None:
            return text
        data = json.loads(text[text.find("{") : text.rfind("}") + 1])
        return schema(**data)

    def _text(self, response: object) -> str:
        return str(getattr(response, "content", "") or "").strip()

    def _rebuild(self, attempt: int) -> None:
        budget = 4096 * (attempt + 2)
        self._client = build_chat_model(budget, self._temperature)
        self._fallback = build_fallback_client(budget, self._temperature)
        time.sleep(2 * (attempt + 1))

    def generate(self, prompt: str, **kwargs: object):
        schema = kwargs.get("schema")
        prompt = self._prepare(prompt, kwargs)
        for attempt in range(3):
            for client in filter(None, (self._client, self._fallback)):
                text = self._text(client.invoke(prompt))
                if not text:
                    continue  # empty content is not an exception
                try:
                    return self._parse(text, schema)
                except (ValueError, TypeError, KeyError):
                    continue  # malformed structured output, try the next client
            self._rebuild(attempt)
        raise RuntimeError("Judge model returned empty content three times in a row.")

    async def a_generate(self, prompt: str, **kwargs: object):
        schema = kwargs.get("schema")
        prompt = self._prepare(prompt, kwargs)
        for attempt in range(3):
            for client in filter(None, (self._client, self._fallback)):
                text = self._text(await client.ainvoke(prompt))
                if not text:
                    continue
                try:
                    return self._parse(text, schema)
                except (ValueError, TypeError, KeyError):
                    continue
            self._rebuild(attempt)
        raise RuntimeError("Judge model returned empty content three times in a row.")


def get_judge() -> EvalJudge:
    """One judge per process; metrics are cheap, model construction is not."""
    global _JUDGE
    if _JUDGE is None:
        _JUDGE = EvalJudge()
    return _JUDGE


_JUDGE: EvalJudge | None = None
