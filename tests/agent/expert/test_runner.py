"""Unit tests for multi-agent runner."""

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.agent.expert.runner import run_expert_review
from src.agent.expert.schemas import (
    AgentIssue,
    AgentNote,
    IssueLocation,
    Severity,
    SpecializedAgentOutput,
    SummaryAgentOutput,
)
from src.agent.tools.changed_files import _changed_files_impl
from tests.test_helper import create_test_repo


def create_mock_message(content: object, usage_metadata: dict) -> Mock:
    """Create a mock message object with content and usage metadata."""
    msg = Mock()
    msg.content = content
    msg.usage_metadata = usage_metadata
    return msg


@pytest.mark.asyncio
async def test_expert_review_happy_flow() -> None:
    """Test expert review with all agents returning successful results."""
    with create_test_repo() as repo_path:
        # Setup: Get changed files using real tools
        changed_files = _changed_files_impl(str(repo_path), "main")

        # Mock specialized agent outputs
        specialized_output = SpecializedAgentOutput(
            issues=[
                AgentIssue(
                    issue_type="test_issue",
                    severity=Severity.MEDIUM,
                    location=IssueLocation(
                        file_path="file1.py", line_start=1, line_end=2
                    ),
                    description="Test issue description",
                    recommendation="Test recommendation",
                    confidence_score=0.9,
                )
            ],
            notes=[AgentNote(note="Test note", context="Additional context")],
        )

        # Mock summary agent output
        summary_output = SummaryAgentOutput(
            markdown_summary="""# Code Review Summary

## Overview
This is a test review summary.

## High Priority Issues ⚠️
- Test issue in file1.py

## Recommendations
- Apply test recommendations
"""
        )

        # Create mock responses for specialized agents
        def create_specialized_response() -> dict:
            return {
                "structured_response": specialized_output,
                "messages": [
                    create_mock_message(
                        specialized_output,
                        usage_metadata={
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "total_tokens": 150,
                        },
                    )
                ],
            }

        # Create mock response for summary agent
        def create_summary_response() -> dict:
            return {
                "structured_response": summary_output,
                "messages": [
                    create_mock_message(
                        summary_output,
                        usage_metadata={
                            "input_tokens": 800,
                            "output_tokens": 200,
                            "total_tokens": 1000,
                        },
                    )
                ],
            }

        # Mock the agent.ainvoke calls
        # We need to mock at the agent level, not the model level
        # The agent is created inside run_specialized_agent and run_summary_agent
        async def mock_ainvoke(*args: Any, **kwargs: Any) -> dict:
            # Determine if this is a summary agent or specialized agent
            # by checking the message content
            messages = args[0].get("messages", [])
            if messages and "synthesize" in messages[0].get("content", "").lower():
                return create_summary_response()
            else:
                return create_specialized_response()

        # Patch create_agent to return an agent with mocked ainvoke
        with patch("src.agent.expert.runner.create_agent") as mock_create_agent:
            mock_agent = Mock()
            mock_agent.ainvoke = AsyncMock(side_effect=mock_ainvoke)
            mock_create_agent.return_value = mock_agent

            # Run expert review without progress output for cleaner test logs
            review_content, token_usage = await run_expert_review(
                str(repo_path),
                "main",
                changed_files,
                show_progress=False,
                additional_instructions=None,
            )

            # Verify review content
            assert isinstance(review_content, str)
            assert len(review_content) > 0
            assert "Code Review Summary" in review_content
            assert "Test issue in file1.py" in review_content

            # Verify token usage is aggregated correctly
            # 8 specialized agents * 150 tokens + 1 summary agent * 1000 tokens = 2200 total
            assert token_usage is not None

            # Check that token usage is aggregated from all agents
            # 8 specialized agents * (100 input + 50 output) + 1 summary (800 input + 200 output)
            expected_input = 8 * 100 + 800  # 1600
            expected_output = 8 * 50 + 200  # 600
            expected_total = expected_input + expected_output  # 2200

            assert token_usage.input_tokens == expected_input
            assert token_usage.output_tokens == expected_output
            assert token_usage.total_tokens == expected_total

            # Verify that agents were called
            # 8 specialized agents + 1 summary agent = 9 total calls
            assert mock_agent.ainvoke.call_count == 9
