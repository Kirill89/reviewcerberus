from typing import Any

from langchain_anthropic import ChatAnthropic

from ...config import ANTHROPIC_API_KEY


def create_anthropic_model(model_name: str, max_tokens: int) -> Any:
    """Create an Anthropic model with automatic prompt caching.

    Args:
        model_name: The Anthropic model identifier
        max_tokens: Maximum tokens for model output

    Returns:
        Configured Anthropic model (caching handled by SDK)
    """
    # Prompt caching is handled automatically by the Anthropic SDK
    return ChatAnthropic(
        model_name=model_name,
        api_key=ANTHROPIC_API_KEY,
        temperature=0.0,
        max_tokens_to_sample=max_tokens,
        timeout=180.0,
        stop=[],
    )
