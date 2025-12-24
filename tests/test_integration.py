from src.agent.runner import run_review
from src.agent.schema import Context
from src.agent.tools.changed_files import _changed_files_impl
from tests.test_helper import create_test_repo


def test_full_review_workflow() -> None:
    """Integration test: full code review workflow from git repo to review output."""
    with create_test_repo() as repo_path:
        # Setup: Get changed files
        changed_files = _changed_files_impl(str(repo_path), "main")

        # Create context
        context = Context(
            repo_path=str(repo_path), target_branch="main", changed_files=changed_files
        )

        # Run review without progress output for cleaner test logs
        review_content, token_usage = run_review(
            context, show_progress=False, additional_instructions=None
        )

        # Verify review content
        assert isinstance(review_content, str)
        assert len(review_content) > 100

        # Verify it mentions the changed files
        assert "file1.py" in review_content or "file3.py" in review_content

        # Verify token usage is returned
        assert token_usage is not None
        assert "total_input_tokens" in token_usage
        assert "output_tokens" in token_usage
        assert "total_tokens" in token_usage
