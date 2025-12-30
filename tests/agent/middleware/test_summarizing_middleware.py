"""Tests for SummarizingMiddleware."""

from typing import Any
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage, HumanMessage

from src.agent.middleware import SummarizingMiddleware


def test_triggers_summarization_above_threshold() -> None:
    """Test that summarization is triggered when token count exceeds threshold."""
    middleware = SummarizingMiddleware()

    # Create state with messages
    messages = [
        HumanMessage(content="test message"),
        AIMessage(content="response"),
    ]
    state: Any = {"messages": messages}

    runtime = Mock()

    # Mock count_tokens_approximately where it's imported in the middleware module
    # CONTEXT_COMPACT_THRESHOLD is 140000 by default
    with patch(
        "src.agent.middleware.summarizing_middleware.count_tokens_approximately"
    ) as mock_count:
        # Below threshold - should not trigger
        mock_count.return_value = 5000
        result = middleware.before_model(state, runtime)
        assert result is None

        # Above threshold - should trigger summarization
        mock_count.return_value = 150000
        result = middleware.before_model(state, runtime)
        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], HumanMessage)
        # Should contain context summary prompt
        assert len(result["messages"][0].content) > 0
