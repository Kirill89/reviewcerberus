from src.agent.tools.read_file import ReadFile
from tests.test_helper import create_test_repo


def test_read_file() -> None:
    """Test that ReadFile reads entire file."""
    with create_test_repo() as repo_path:
        tracker = ReadFile()

        result = tracker._read_full_file(str(repo_path), "file1.py")

        assert result.file_path == "file1.py"
        assert result.total_lines == 3
        assert "def hello():" in result.content
        assert not result.was_truncated


def test_read_file_prevents_duplicate() -> None:
    """Test that ReadFile tracks accessed files."""
    with create_test_repo() as repo_path:
        tracker = ReadFile()

        # Read a file
        tracker._read_full_file(str(repo_path), "file1.py")
        tracker._record_access("file1.py")

        # Check it's marked as read
        assert tracker._check_already_read("file1.py")
        assert not tracker._check_already_read("file2.py")
