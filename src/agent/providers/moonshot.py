import warnings
from typing import Any, Sequence

from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from ...config import MOONSHOT_API_BASE, MOONSHOT_API_KEY


class MoonshotChat(ChatOpenAI):
    """ChatOpenAI subclass that overrides bind_tools to use tool_choice='auto'."""

    def bind_tools(
        self,
        tools: Sequence[BaseTool | type | dict[str, Any] | Any],
        **kwargs: Any,
    ) -> Any:
        """Bind tools with tool_choice forced to 'auto' for Kimi K2.5 compatibility."""
        if "tool_choice" in kwargs and kwargs["tool_choice"] != "auto":
            warnings.warn(
                f"Moonshot: tool_choice='{kwargs['tool_choice']}' overridden to 'auto' "
                "for Kimi K2.5 compatibility",
                UserWarning,
                stacklevel=2,
            )
        kwargs["tool_choice"] = "auto"
        return super().bind_tools(tools, **kwargs)


def create_moonshot_model(model_name: str, max_tokens: int) -> Any:
    """Create a Moonshot model for inference.

    Uses ChatOpenAI with Moonshot's OpenAI-compatible API for full tool support.
    Moonshot supports automatic context caching server-side (no config needed).
    See: https://platform.moonshot.ai/docs/pricing/chat

    Args:
        model_name: The Moonshot model identifier (e.g., "kimi-k2.5")
        max_tokens: Maximum tokens for model output

    Returns:
        Configured Moonshot model
    """
    # kimi-k2.5: disable thinking mode for tool_choice compatibility
    # Instant mode uses temperature=0.6, top_p=0.95
    # See: https://platform.moonshot.ai/docs/guide/kimi-k2-5-quickstart
    return MoonshotChat(
        model=model_name,
        api_key=MOONSHOT_API_KEY,
        base_url=MOONSHOT_API_BASE,
        temperature=0.6,
        top_p=0.95,
        max_completion_tokens=max_tokens,
        timeout=180.0,
        extra_body={
            "thinking": {
                "type": "disabled",
            },
        },
    )
