"""Tests for formatting utilities."""

from src.agent.expert.schemas import (
    AgentIssue,
    AgentNote,
    IssueLocation,
    Severity,
    SpecializedAgentOutput,
)
from src.agent.formatting import format_agent_statistics


def test_format_agent_statistics() -> None:
    """Test that agent information is formatted correctly."""
    agent_stats = {
        "security": {
            "steps": 50,
            "llm_calls": 10,
            "tool_calls": 20,
            "recursion_limit": 600,
            "remaining": 550,
        },
        "code_quality": {
            "steps": 120,
            "llm_calls": 25,
            "tool_calls": 45,
            "recursion_limit": 600,
            "remaining": 480,
        },
        "summary": {
            "steps": 30,
            "llm_calls": 5,
            "tool_calls": 10,
            "recursion_limit": 600,
            "remaining": 570,
        },
    }

    result = format_agent_statistics(agent_stats)

    # Check for section header
    assert "## Agents" in result

    # Check for agent subsections (sorted alphabetically, excluding summary)
    assert "### Code Quality" in result
    assert "### Security" in result
    assert "### Summary" not in result  # Summary should be excluded

    # Check for separator
    assert "---" in result


def test_format_agent_statistics_underscore_names() -> None:
    """Test that agent names with underscores are formatted nicely."""
    agent_stats = {
        "error_handling": {
            "steps": 100,
            "llm_calls": 20,
            "tool_calls": 30,
            "recursion_limit": 600,
            "remaining": 500,
        },
    }

    result = format_agent_statistics(agent_stats)

    # Check that underscores are replaced and title-cased
    assert "### Error Handling" in result
    assert "error_handling" not in result


def test_format_agent_statistics_with_outputs() -> None:
    """Test that agent outputs (issues and notes) are included."""
    agent_stats = {
        "security": {
            "steps": 50,
            "llm_calls": 10,
            "tool_calls": 20,
            "recursion_limit": 600,
            "remaining": 550,
        },
    }

    agent_outputs = {
        "security": SpecializedAgentOutput(
            issues=[
                AgentIssue(
                    issue_type="SQL Injection",
                    severity=Severity.CRITICAL,
                    location=IssueLocation(
                        file_path="app/models.py", line_start=42, line_end=45
                    ),
                    description="User input not sanitized before SQL query",
                    recommendation="Use parameterized queries",
                    confidence_score=0.95,
                ),
            ],
            notes=[
                AgentNote(
                    note="Consider implementing rate limiting",
                    context="API endpoints are exposed",
                ),
            ],
        ),
    }

    result = format_agent_statistics(agent_stats, agent_outputs)

    # Check issues are included
    assert "**Issues:**" in result
    assert "**[CRITICAL]** app/models.py:42 - User input not sanitized" in result

    # Check notes are included
    assert "**Notes:**" in result
    assert "- Consider implementing rate limiting" in result
