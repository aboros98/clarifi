from langchain_google_genai import ChatGoogleGenerativeAI

from clarifi.config import settings

_llm_cache: dict[str, ChatGoogleGenerativeAI] = {}


def get_llm(model: str | None = None) -> ChatGoogleGenerativeAI:
    """Return a cached LLM instance. Reuses connections across calls."""
    model = model or settings.llm_model
    if model not in _llm_cache:
        _llm_cache[model] = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.google_api_key,
            temperature=0,
        )
    return _llm_cache[model]
