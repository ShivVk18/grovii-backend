from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import limits
from src.config.config import settings
from src.services.llm_usage import UsageCallback


def _chat_model(node: str, **kwargs) -> ChatGoogleGenerativeAI:
    """Build the provider client (Google Gemini). Kept separate so tests can
    swap in a fake. `node` is only for identification; it is not sent."""
    return ChatGoogleGenerativeAI(**kwargs)


class OpenAiService:
    # Name kept so existing imports keep working; the provider is now Gemini.

    def get_llm(self, node: str | None = None, model: str | None = None, temperature: float = 0.7):
        """Create a chat model for one graph node.

        Every model gets: a request timeout, a bounded number of retries, an
        output-token cap for its node, and a callback that meters token usage
        against the current job's budget. Pass the graph node name.
        """
        name = node or "unknown"
        kwargs = dict(
            google_api_key=settings.GEMINI_API_KEY,
            model=model or limits.LLM_MODEL,
            temperature=temperature,
            timeout=limits.LLM_TIMEOUT_SECONDS,
            max_retries=limits.LLM_MAX_RETRIES,
            max_output_tokens=limits.NODE_MAX_OUTPUT_TOKENS.get(name, limits.DEFAULT_MAX_OUTPUT_TOKENS),
            callbacks=[UsageCallback(name)],
        )
        if limits.LLM_BASE_URL:
            kwargs["base_url"] = limits.LLM_BASE_URL
        return _chat_model(node=name, **kwargs)


openai_service = OpenAiService()
llm_service = openai_service
