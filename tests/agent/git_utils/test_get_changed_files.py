"""Tests for get_changed_files."""

from src.agent.git_utils import get_changed_files
from tests.test_helper import create_test_repo


def test_get_changed_files_returns_modified_and_added() -> None:
    """Test that get_changed_files returns both modified and added files."""
    with create_test_repo() as repo_path:
        changes = get_changed_files(str(repo_path), "main")

        assert len(changes) == 2

        paths = {c.path for c in changes}
        assert "file1.py" in paths
        assert "file3.py" in paths

        file1 = next(c for c in changes if c.path == "file1.py")
        assert file1.change_type == "modified"
        assert file1.additions > 0

        file3 = next(c for c in changes if c.path == "file3.py")
        assert file3.change_type == "added"
