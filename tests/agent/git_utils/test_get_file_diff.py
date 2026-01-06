"""Tests for get_file_diff."""

from src.agent.git_utils import get_file_diff
from tests.test_helper import create_test_repo


def test_get_file_diff_returns_diff() -> None:
    """Test that get_file_diff returns diff content for a changed file."""
    with create_test_repo() as repo_path:
        diff = get_file_diff(str(repo_path), "main", "file1.py")

        assert diff is not None
        assert "hello world" in diff
        assert "return True" in diff
