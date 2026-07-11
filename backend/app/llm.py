"""
Thin wrapper around Groq's chat completion API.

Primary model: gemma2-9b-it (per assignment spec — fast, cheap, good enough
for extraction/summarization on short interaction notes).

Fallback model: llama-3.3-70b-versatile — used automatically when the
primary model errors out (rate limit, transient failure) or when a task
is flagged as needing stronger reasoning (e.g. multi-step follow-up
planning), giving the agent more context/capability at the cost of speed.
"""

from __future__ import annotations

import json
import logging

from groq import Groq

from app.config import settings

logger = logging.getLogger("hcp_crm.llm")

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def chat_completion(
    messages: list[dict],
    *,
    use_fallback_model: bool = False,
    json_mode: bool = False,
    temperature: float = 0.2,
) -> str:
    """Call Groq chat completions, retrying on the fallback model on failure.

    `messages` follows the standard OpenAI-style [{"role": ..., "content": ...}] shape.
    """
    client = _get_client()
    model = settings.groq_fallback_model if use_fallback_model else settings.groq_primary_model

    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            **kwargs,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001 - deliberately broad, we fall back
        if not use_fallback_model:
            logger.warning("Primary model %s failed (%s); retrying on fallback model", model, exc)
            return chat_completion(
                messages, use_fallback_model=True, json_mode=json_mode, temperature=temperature
            )
        raise


def extract_json(messages: list[dict], **kwargs) -> dict:
    """Call chat_completion in JSON mode and safely parse the result."""
    raw = chat_completion(messages, json_mode=True, **kwargs)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Model did not return valid JSON: %s", raw[:500])
        return {}
