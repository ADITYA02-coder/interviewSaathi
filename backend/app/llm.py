"""Provider-agnostic LLM access. If nothing is configured the interviewer falls back to the offline engine."""
import json
import re
import httpx
from .config import settings

_transport = None  # tests inject httpx.MockTransport


class LLMUnavailable(Exception):
    pass


def provider() -> str:
    p = settings.llm_provider
    if p == "anthropic" and settings.anthropic_api_key:
        return "anthropic"
    if p == "openai" and settings.openai_api_key:
        return "openai"
    if p == "auto":
        if settings.anthropic_api_key:
            return "anthropic"
        if settings.openai_api_key:
            return "openai"
    return "none"


def engine_name() -> str:
    p = provider()
    return {"anthropic": f"anthropic:{settings.anthropic_model}", "openai": f"openai-compatible:{settings.openai_model}"}.get(p, "offline-rule-based")


async def complete(system: str, messages: list[dict], max_tokens: int = 700, temperature: float = 0.7) -> str:
    p = provider()
    if p == "none":
        raise LLMUnavailable("No LLM configured")
    try:
        async with httpx.AsyncClient(timeout=40, transport=_transport) as c:
            if p == "anthropic":
                r = await c.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01"},
                    json={"model": settings.anthropic_model, "max_tokens": max_tokens, "temperature": temperature,
                          "system": system, "messages": messages},
                )
                r.raise_for_status()
                return "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
            r = await c.post(
                f"{settings.openai_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={"model": settings.openai_model, "max_tokens": max_tokens, "temperature": temperature,
                      "messages": [{"role": "system", "content": system}, *messages]},
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, ValueError) as e:
        raise LLMUnavailable(str(e))


def parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise LLMUnavailable("Model did not return JSON")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise LLMUnavailable(f"Bad JSON from model: {e}")


async def complete_json(system: str, messages: list[dict], **kw) -> dict:
    return parse_json(await complete(system, messages, **kw))
