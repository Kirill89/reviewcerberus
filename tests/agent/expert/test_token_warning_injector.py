from unittest.mock import Mock

from src.agent.expert.token_warning_injector import TokenWarningInjector


def test_token_warning_injector_initialization() -> None:
    """Test TokenWarningInjector initialization."""
    injector = TokenWarningInjector(max_context_window=100000)

    assert injector.max_context_window == 100000
    assert injector.total_tokens == 0
    assert len(injector.warnings_sent) == 0
    assert len(injector.warning_thresholds) == 8


def test_token_warning_injector_tracks_tokens() -> None:
    """Test TokenWarningInjector tracks tokens via on_llm_end callback."""
    injector = TokenWarningInjector(max_context_window=100000)

    # Mock response with usage metadata
    generation = Mock()
    generation.message.usage_metadata = {"total_tokens": 1000}

    response = Mock()
    response.generations = [[generation]]

    # Call on_llm_end to track tokens
    injector.on_llm_end(response)

    assert injector.total_tokens == 1000

    # Simulate another call with cumulative total
    generation.message.usage_metadata = {"total_tokens": 2500}
    injector.on_llm_end(response)

    assert injector.total_tokens == 2500


def test_token_warning_injector_injects_warning_at_threshold() -> None:
    """Test TokenWarningInjector injects warning when threshold is crossed."""
    injector = TokenWarningInjector(max_context_window=100000)

    # Set total tokens to cross 40% threshold (40,000 tokens)
    injector.total_tokens = 45000

    # Mock state and runtime
    state = Mock()
    runtime = Mock()

    # Call before_model to check if warning is injected
    result = injector.before_model(state, runtime)

    assert result is not None
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert 0.4 in injector.warnings_sent

    # Call again - should not inject duplicate warning
    result = injector.before_model(state, runtime)
    assert result is None


def test_token_warning_injector_no_warning_below_threshold() -> None:
    """Test TokenWarningInjector does not inject warning below threshold."""
    injector = TokenWarningInjector(max_context_window=100000)

    # Set total tokens below first threshold (40%)
    injector.total_tokens = 30000

    # Mock state and runtime
    state = Mock()
    runtime = Mock()

    # Call before_model - should not inject warning
    result = injector.before_model(state, runtime)

    assert result is None
    assert len(injector.warnings_sent) == 0
