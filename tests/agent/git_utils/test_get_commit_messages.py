"""Tests for get_commit_messages."""

from src.agent.git_utils import get_commit_messages
from tests.test_helper import create_test_repo


def test_get_commit_messages_returns_commits() -> None:
    """Test that get_commit_messages returns commits between branches."""
    with create_test_repo() as repo_path:
        commits = get_commit_messages(str(repo_path), "main")

        assert len(commits) == 1
        assert commits[0].message == "Add feature"
        assert commits[0].author == "Test User"
        assert len(commits[0].sha) == 40
