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
    VerificationAgentOutput,
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

        # Mock verification agent output - returns accepted IDs
        # For simplicity, verification agent accepts all findings in this test
        verification_output = VerificationAgentOutput(
            accepted_issue_ids=[
                "security_issue_0",
                "code_quality_issue_0",
                "performance_issue_0",
                "architecture_issue_0",
                "documentation_issue_0",
                "error_handling_issue_0",
                "business_logic_issue_0",
                "testing_issue_0",
            ],
            accepted_note_ids=[
                "security_note_0",
                "code_quality_note_0",
                "performance_note_0",
                "architecture_note_0",
                "documentation_note_0",
                "error_handling_note_0",
                "business_logic_note_0",
                "testing_note_0",
            ],
            verification_notes=["All findings verified as legitimate"],
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

        # Create mock response for verification agent
        def create_verification_response() -> dict:
            return {
                "structured_response": verification_output,
                "messages": [
                    create_mock_message(
                        verification_output,
                        usage_metadata={
                            "input_tokens": 400,
                            "output_tokens": 100,
                            "total_tokens": 500,
                        },
                    )
                ],
            }

        # Mock the agent.ainvoke calls
        # We need to mock at the agent level, not the model level
        # The agent is created inside run_specialized_agent, run_verification_agent, and run_summary_agent
        async def mock_ainvoke(*args: Any, **kwargs: Any) -> dict:
            # Determine which agent this is by checking the message content
            messages = args[0].get("messages", [])
            if messages:
                content = messages[0].get("content", "").lower()
                if "synthesize" in content:
                    return create_summary_response()
                elif "verify all findings" in content or "false positives" in content:
                    return create_verification_response()
            return create_specialized_response()

        # Patch create_agent in all agent modules
        with patch(
            "src.agent.expert.agents.specialized_agent.create_agent"
        ) as mock_specialized_create, patch(
            "src.agent.expert.agents.verification_agent.create_agent"
        ) as mock_verification_create, patch(
            "src.agent.expert.agents.summary_agent.create_agent"
        ) as mock_summary_create:
            mock_agent = Mock()
            mock_agent.ainvoke = AsyncMock(side_effect=mock_ainvoke)

            # Set all mocks to return the same mock agent
            mock_specialized_create.return_value = mock_agent
            mock_verification_create.return_value = mock_agent
            mock_summary_create.return_value = mock_agent

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
            assert "Verification Agent Notes" in review_content

            # Verify token usage is aggregated correctly
            # 8 specialized agents * 150 tokens + 1 verification agent * 500 tokens + 1 summary agent * 1000 tokens
            assert token_usage is not None

            # Check that token usage is aggregated from all agents
            # 8 specialized (100 input + 50 output) + 1 verification (400 input + 100 output) + 1 summary (800 input + 200 output)
            expected_input = 8 * 100 + 400 + 800  # 2000
            expected_output = 8 * 50 + 100 + 200  # 700
            expected_total = expected_input + expected_output  # 2700

            assert token_usage.input_tokens == expected_input
            assert token_usage.output_tokens == expected_output
            assert token_usage.total_tokens == expected_total

            # Verify that agents were called
            # 8 specialized agents + 1 verification agent + 1 summary agent = 10 total calls
            assert mock_agent.ainvoke.call_count == 10
