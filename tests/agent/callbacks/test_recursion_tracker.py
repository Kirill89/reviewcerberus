"""Tests for RecursionTracker callback and middleware."""

from typing import Any
from unittest.mock import Mock

import pytest
from langchain_core.messages import HumanMessage

from src.agent.callbacks import RecursionTracker


def test_recursion_tracker_counts_steps() -> None:
    """Test that RecursionTracker accurately counts chain steps."""
    tracker = RecursionTracker(recursion_limit=100, agent_name="test_agent")

    assert tracker.step_count == 0
    assert tracker.llm_calls == 0
    assert tracker.tool_calls == 0

    # Simulate chain starts
    tracker.on_chain_start({}, {})
    assert tracker.step_count == 1

    tracker.on_chain_start({}, {})
    assert tracker.step_count == 2

    # Simulate LLM calls
    tracker.on_llm_start({}, ["prompt"])
    assert tracker.llm_calls == 1

    # Simulate tool calls
    tracker.on_tool_start({}, "input")
    assert tracker.tool_calls == 1

    stats = tracker.get_stats()
    assert stats["steps"] == 2
    assert stats["llm_calls"] == 1
    assert stats["tool_calls"] == 1
    assert stats["recursion_limit"] == 100
    assert stats["remaining"] == 98


def test_recursion_tracker_middleware_warns_at_thresholds(
    capsys: pytest.CaptureFixture,
) -> None:
    """Test that RecursionTracker injects warnings via middleware at correct thresholds."""
    tracker = RecursionTracker(recursion_limit=100, agent_name="test_agent")

    # Mock state and runtime
    state: dict[str, list[Any]] = {"messages": []}
    runtime = Mock()
    runtime.context = Mock()

    # Simulate 49 steps via callback (below 50% threshold)
    for _ in range(49):
        tracker.on_chain_start({}, {})

    # Call middleware - should not warn yet
    result = tracker.before_model(state, runtime)  # type: ignore[type-var]
    assert result is None
    captured = capsys.readouterr()
    assert "⚠️" not in captured.out

    # Step 50 should trigger 50% warning when middleware checks
    tracker.on_chain_start({}, {})
    result = tracker.before_model(state, runtime)  # type: ignore[type-var]

    assert result is not None
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], HumanMessage)
    assert "50% of your allowed tool calls" in result["messages"][0].content
    assert "__RECURSION_BUDGET_WARNING__50" in result["messages"][0].content

    captured = capsys.readouterr()
    assert "⚠️  [test_agent] Recursion budget warning: 50% used" in captured.out
    assert "50 remaining" in captured.out

    # Add the warning message to state to simulate it being added
    state["messages"].append(result["messages"][0])

    # Should not warn again at 50%
    tracker.on_chain_start({}, {})
    result = tracker.before_model(state, runtime)  # type: ignore[type-var]
    assert result is None

    # Simulate to 70% threshold
    for _ in range(19):  # 51 -> 70
        tracker.on_chain_start({}, {})

    result = tracker.before_model(state, runtime)  # type: ignore[type-var]
    assert result is not None
    captured = capsys.readouterr()
    assert "⚠️  [test_agent] Recursion budget warning: 70% used" in captured.out


def test_recursion_tracker_middleware_no_duplicate_warnings() -> None:
    """Test that RecursionTracker doesn't inject duplicate warnings."""
    tracker = RecursionTracker(recursion_limit=100, agent_name="test_agent")

    # Mock state with existing warning marker
    existing_warning = HumanMessage(
        content="Warning message\n\n<!-- __RECURSION_BUDGET_WARNING__50 -->"
    )
    state = {"messages": [existing_warning]}
    runtime = Mock()
    runtime.context = Mock()

    # Cross 50% threshold
    for _ in range(50):
        tracker.on_chain_start({}, {})

    # Should not inject warning again because marker exists
    result = tracker.before_model(state, runtime)  # type: ignore[type-var]
    assert result is None


def test_recursion_tracker_no_warning_above_limit() -> None:
    """Test that RecursionTracker doesn't warn when already over limit."""
    tracker = RecursionTracker(recursion_limit=10, agent_name="test_agent")

    state: dict[str, list[Any]] = {"messages": []}
    runtime = Mock()
    runtime.context = Mock()

    # Simulate going past the limit
    for i in range(15):
        tracker.on_chain_start({}, {})
        result = tracker.before_model(state, runtime)  # type: ignore[type-var]
        if result and "messages" in result:
            state["messages"].extend(result["messages"])

    # Should have warned at thresholds but not after exceeding limit
    warning_messages = [
        msg
        for msg in state["messages"]
        if isinstance(msg, HumanMessage)
        and "RECURSION BUDGET WARNING" in str(msg.content)
    ]

    # Should have warnings for 50%, 70%, 85% thresholds only
    assert len(warning_messages) == 3
