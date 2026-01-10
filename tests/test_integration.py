from src.agent.formatting import format_review_content, render_structured_output
from src.agent.git_utils import get_changed_files
from src.agent.runner import run_review
from src.agent.schema import PrimaryReviewOutput
from tests.test_helper import create_test_repo


def test_full_review_workflow() -> None:
    """Integration test: full code review workflow from git repo to review output."""
    with create_test_repo() as repo_path:
        # Setup: Get changed files
        changed_files = get_changed_files(str(repo_path), "main")

        # Run review without progress output for cleaner test logs
        # Use additional instructions to keep the review very brief for faster testing
        review_result = run_review(
            repo_path=str(repo_path),
            target_branch="main",
            changed_files=changed_files,
            show_progress=False,
            additional_instructions="Keep this review extremely brief (max 3-4 sentences total). Only mention the most critical findings.",
        )

        # Verify structured output
        assert isinstance(review_result.output, PrimaryReviewOutput)
        assert isinstance(review_result.output.description, str)
        assert len(review_result.output.description) > 50
        assert isinstance(review_result.output.issues, list)

        # Render and format the output
        review_content = render_structured_output(review_result.output)
        review_content = format_review_content(review_content)

        # Verify rendered content
        assert isinstance(review_content, str)
        assert len(review_content) > 100

        # Verify token usage is returned
        assert review_result.token_usage is not None
        assert review_result.token_usage.input_tokens > 0
        assert review_result.token_usage.output_tokens > 0
        assert review_result.token_usage.total_tokens > 0
