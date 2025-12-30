"""Tests for ToolDeduplicationMiddleware."""

from typing import Any
from unittest.mock import Mock

from langchain_core.messages import AIMessage

from src.agent.middleware import ToolDeduplicationMiddleware


def test_blocks_duplicate_tool_calls() -> None:
    """Test that duplicate tool calls are blocked."""
    middleware = ToolDeduplicationMiddleware(window_size=10)

    # Create tool call as dict (required format for AIMessage)
    tool_call_dict = {
        "name": "read_file",
        "args": {"file_path": "test.py", "start_line": 1},
        "id": "call_123",
        "type": "tool_call",
    }

    # Create AI message with tool call
    ai_message = AIMessage(content="", tool_calls=[tool_call_dict])

    # Create mock state with the AI message
    state: Any = {"messages": [ai_message]}

    # Create mock runtime with context
    runtime = Mock()
    runtime.context = Mock()
    runtime.context.agent_name = "test_agent"

    # First call - should return None (no duplicate)
    result = middleware.before_model(state, runtime)
    assert result is None

    # Second call with same tool - should return warning message
    result = middleware.before_model(state, runtime)
    assert result is not None
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert "WARNING" in result["messages"][0].content
    assert "read_file" in result["messages"][0].content
