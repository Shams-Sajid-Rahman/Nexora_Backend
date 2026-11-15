"""LLM provider abstraction (docs/05 §5.9, docs/01 §1.8).

No other module calls a provider SDK directly. When LLM_PROVIDER is not
configured, the NullProvider returns a clearly-labelled stub reply and
no external call is made. Real providers implement the same interface
and are selected purely from environment (LLM_PROVIDER / LLM_API_KEY /
LLM_MODEL) — no key is ever committed.
"""
from app.core.config import settings


class LLMProvider:
    name = "null"

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        raise NotImplementedError


class NullProvider(LLMProvider):
    """No LLM configured. Returns a labelled stub so the API, logging and
    tool pipeline can be exercised without a key or a network call."""
    name = "null"

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        return {
            "content": ("[AI-generated] No LLM provider is configured "
                        "(set LLM_PROVIDER / LLM_API_KEY / LLM_MODEL). "
                        "I can still run the approved read-only business tools "
                        "and summarise their verified results."),
            "tool_calls": [],
        }


class EchoProvider(LLMProvider):
    """Test/dev provider: echoes the last user message, labelled."""
    name = "echo"

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        last = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        return {"content": f"[AI-generated] Echo (dev provider): {last}", "tool_calls": []}


def get_provider() -> LLMProvider:
    if settings.llm_provider == "echo":
        return EchoProvider()
    # A real provider (e.g. openai/anthropic/ollama) would be added here
    # behind the same interface, reading settings.llm_api_key.
    return NullProvider()
