from typing import Any

from langchain_ollama import ChatOllama

from ...config import OLLAMA_BASE_URL


def create_ollama_model(model_name: str, max_tokens: int) -> Any:
    """Create an Ollama model for local inference.

    Args:
        model_name: The Ollama model identifier (e.g., "devstral-small-2:24b-cloud")
        max_tokens: Maximum tokens for model output

    Returns:
        Configured Ollama model
    """
    return ChatOllama(
        model=model_name,
        base_url=OLLAMA_BASE_URL,
        temperature=0.0,
        num_predict=max_tokens,
    )
