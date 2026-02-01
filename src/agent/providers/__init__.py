from typing import Any

from ...config import (
    MAX_OUTPUT_TOKENS,
    MODEL_NAME,
    MODEL_PROVIDER,
)
from .anthropic import create_anthropic_model
from .bedrock import create_bedrock_model
from .moonshot import create_moonshot_model
from .ollama import create_ollama_model

# Registry mapping provider names to factory functions
PROVIDER_REGISTRY = {
    "bedrock": create_bedrock_model,
    "anthropic": create_anthropic_model,
    "ollama": create_ollama_model,
    "moonshot": create_moonshot_model,
}


def create_model() -> Any:
    """Factory function to create model based on MODEL_PROVIDER config.

    Returns:
        Configured model instance ready for use with langchain agents.

    Raises:
        ValueError: If MODEL_PROVIDER is not supported.
    """
    factory = PROVIDER_REGISTRY.get(MODEL_PROVIDER)

    if factory is None:
        supported = ", ".join(PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"Unsupported MODEL_PROVIDER: {MODEL_PROVIDER}. "
            f"Supported providers: {supported}"
        )

    return factory(
        model_name=MODEL_NAME,
        max_tokens=MAX_OUTPUT_TOKENS,
    )
