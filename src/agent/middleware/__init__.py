"""Agent middleware utilities."""

from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware

from ...config import MODEL_PROVIDER
from .recursion_guard import RecursionGuard, ToolCallLimitExceeded
from .summarizing_middleware import SummarizingMiddleware

__all__ = [
    "RecursionGuard",
    "SummarizingMiddleware",
    "ToolCallLimitExceeded",
    "init_agent_middleware",
]


def init_agent_middleware(
    *,
    include_summarizing: bool = False,
) -> list[AgentMiddleware[Any, Any]]:
    """Initialize middleware list for agents.

    Args:
        include_summarizing: Whether to include SummarizingMiddleware for
            context compaction on long conversations.

    Returns:
        List of middleware instances configured based on MODEL_PROVIDER
        and function arguments.
    """
    middleware: list[AgentMiddleware[Any, Any]] = []

    # Always include RecursionGuard
    middleware.append(RecursionGuard())

    # Add SummarizingMiddleware if requested
    if include_summarizing:
        middleware.append(SummarizingMiddleware())

    # Add AnthropicPromptCachingMiddleware only for Anthropic provider
    if MODEL_PROVIDER == "anthropic":
        middleware.append(
            AnthropicPromptCachingMiddleware(
                ttl="5m",
                min_messages_to_cache=1,
            )
        )

    return middleware
