"""Tests for get_file_diff."""

import pytest

from src.agent.formatting.build_review_context import build_review_context
from src.agent.git_utils import get_changed_files, get_file_diff
from tests.test_helper import create_test_repo


def test_get_file_diff_returns_diff() -> None:
    """Test that get_file_diff returns diff content for a changed file."""
    with create_test_repo() as repo_path:
        diff = get_file_diff(str(repo_path), "main", "file1.py")

        assert diff is not None
        assert "hello world" in diff
        assert "return True" in diff


@pytest.mark.parametrize(
    ("contents", "expected"),
    [
        (b"# caf\xc3(\nreturn 42\n", "# caf\ufffd("),
        (b"# caf\xe9\nreturn 42\n", "# caf\ufffd"),
        ("# café\nreturn 42\n".encode("utf-8"), "# café"),
    ],
    ids=["invalid-utf8", "latin1", "valid-utf8"],
)
def test_review_context_handles_file_encodings(contents: bytes, expected: str) -> None:
    with create_test_repo({"legacy.py": contents}) as repo_path:
        diff = get_file_diff(str(repo_path), "main", "legacy.py")
        assert diff is not None
        assert f"+{expected}" in diff
        assert "+return 42" in diff

        context = build_review_context(
            str(repo_path), "main", get_changed_files(str(repo_path), "main")
        )
        assert "### legacy.py" in context
        assert f"+{expected}" in context
        assert "+return 42" in context
        assert (repo_path / "legacy.py").read_bytes() == contents
