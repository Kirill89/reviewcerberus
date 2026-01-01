from unittest.mock import Mock

from src.agent.token_usage import TokenUsage


def test_token_usage_from_response() -> None:
    """Test TokenUsage construction from agent response."""
    # Mock response with usage_metadata
    msg1 = Mock()
    msg1.usage_metadata = {"output_tokens": 100, "total_tokens": 500}

    msg2 = Mock()
    msg2.usage_metadata = {"output_tokens": 50, "total_tokens": 700}

    response = {"messages": [msg1, msg2]}

    usage = TokenUsage.from_response(response)

    assert usage is not None
    assert usage.output_tokens == 150  # 100 + 50
    assert usage.total_tokens == 700  # Final cumulative
    assert usage.input_tokens == 550  # 700 - 150


def test_token_usage_add() -> None:
    """Test adding two TokenUsage instances."""
    usage1 = TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150)
    usage2 = TokenUsage(input_tokens=200, output_tokens=75, total_tokens=275)

    combined = usage1 + usage2

    assert combined.input_tokens == 300
    assert combined.output_tokens == 125
    assert combined.total_tokens == 425


def test_token_usage_from_response_no_messages() -> None:
    """Test TokenUsage.from_response with no messages."""
    response: dict[str, list] = {"messages": []}

    usage = TokenUsage.from_response(response)

    assert usage is None
