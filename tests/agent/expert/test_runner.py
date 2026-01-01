from unittest.mock import Mock, patch

from src.agent.expert.runner import run_expert_review
from src.agent.expert.schemas import (
    ChangesSummary,
    Location,
    PrimaryReviewOutput,
    ReviewFinding,
    Severity,
    ValidatedReviewFinding,
    ValidationOutput,
)
from src.agent.tools.changed_files import _changed_files_impl
from tests.test_helper import create_test_repo


def test_run_expert_review_with_findings() -> None:
    """Test run_expert_review end-to-end with mocked LLM responses."""
    with create_test_repo() as repo_path:
        # Get changed files
        changed_files = _changed_files_impl(str(repo_path), "main")
        assert len(changed_files) > 0

        # Mock the primary review agent response
        primary_response = {
            "structured_response": PrimaryReviewOutput(
                summary=ChangesSummary(
                    changes_title="Test changes",
                    changes_description="Added new Python files for testing",
                ),
                findings=[
                    ReviewFinding(
                        title="Missing error handling",
                        description="Function lacks try-except block",
                        location=[
                            Location(filepath="file1.py", line_start=5, line_end=10)
                        ],
                        recommendation="Add error handling for edge cases",
                        severity=Severity.HIGH,
                    ),
                    ReviewFinding(
                        title="Code style issue",
                        description="Variable name not descriptive",
                        location=[
                            Location(filepath="file2.py", line_start=3, line_end=3)
                        ],
                        recommendation="Rename variable to be more descriptive",
                        severity=Severity.LOW,
                    ),
                ],
            ),
            "messages": [
                Mock(
                    usage_metadata={
                        "input_tokens": 1000,
                        "output_tokens": 500,
                        "total_tokens": 1500,
                    }
                )
            ],
        }

        # Mock the validation agent response
        validation_response = {
            "structured_response": ValidationOutput(
                findings=[
                    ValidatedReviewFinding(
                        title="Missing error handling",
                        description="Function lacks try-except block",
                        location=[
                            Location(filepath="file1.py", line_start=5, line_end=10)
                        ],
                        recommendation="Add error handling for edge cases",
                        severity=Severity.HIGH,
                        confirmed=True,
                        validation_reason="Confirmed: Error handling is indeed missing",
                    ),
                    ValidatedReviewFinding(
                        title="Code style issue",
                        description="Variable name not descriptive",
                        location=[
                            Location(filepath="file2.py", line_start=3, line_end=3)
                        ],
                        recommendation="Rename variable to be more descriptive",
                        severity=Severity.LOW,
                        confirmed=False,
                        validation_reason="Rejected: Variable name is acceptable for context",
                    ),
                ]
            ),
            "messages": [
                Mock(
                    usage_metadata={
                        "input_tokens": 800,
                        "output_tokens": 300,
                        "total_tokens": 1100,
                    }
                )
            ],
        }

        # Mock the model to return both responses in sequence
        mock_agent = Mock()
        mock_agent.invoke.side_effect = [primary_response, validation_response]

        # Patch the create_agent function to return our mock
        with patch(
            "src.agent.expert.agent_factory.create_agent", return_value=mock_agent
        ):
            # Run the expert review
            review_content, token_usage = run_expert_review(
                repo_path=str(repo_path),
                target_branch="main",
                changed_files=changed_files,
                show_progress=False,
                max_context_window=100000,
            )

        # Verify output
        assert isinstance(review_content, str)
        assert len(review_content) > 0

        # Verify the markdown content contains key elements
        assert "Test changes" in review_content
        assert "Missing error handling" in review_content
        assert "file1.py" in review_content
        # Only confirmed findings appear in markdown (rejected findings are in console stats only)
        assert "High Severity" in review_content
        assert "1 confirmed" in review_content

        # Verify token usage is combined from both stages
        assert token_usage is not None
        assert token_usage.input_tokens == 1800  # 1000 + 800
        assert token_usage.output_tokens == 800  # 500 + 300
        assert token_usage.total_tokens == 2600  # 1500 + 1100

        # Verify agent was invoked twice (primary + validation)
        assert mock_agent.invoke.call_count == 2


def test_run_expert_review_no_findings() -> None:
    """Test run_expert_review when no findings are identified."""
    with create_test_repo() as repo_path:
        # Get changed files
        changed_files = _changed_files_impl(str(repo_path), "main")
        assert len(changed_files) > 0

        # Mock the primary review agent response with no findings
        primary_response = {
            "structured_response": PrimaryReviewOutput(
                summary=ChangesSummary(
                    changes_title="Clean changes",
                    changes_description="No issues found",
                ),
                findings=[],
            ),
            "messages": [
                Mock(
                    usage_metadata={
                        "input_tokens": 1000,
                        "output_tokens": 200,
                        "total_tokens": 1200,
                    }
                )
            ],
        }

        # Mock the model
        mock_agent = Mock()
        mock_agent.invoke.return_value = primary_response

        # Patch the create_agent function
        with patch(
            "src.agent.expert.agent_factory.create_agent", return_value=mock_agent
        ):
            # Run the expert review
            review_content, token_usage = run_expert_review(
                repo_path=str(repo_path),
                target_branch="main",
                changed_files=changed_files,
                show_progress=False,
                max_context_window=100000,
            )

        # Verify output
        assert isinstance(review_content, str)
        assert len(review_content) > 0
        assert "Clean changes" in review_content

        # Verify token usage is only from stage 1
        assert token_usage is not None
        assert token_usage.input_tokens == 1000
        assert token_usage.output_tokens == 200
        assert token_usage.total_tokens == 1200

        # Verify agent was invoked only once (validation skipped)
        assert mock_agent.invoke.call_count == 1
