from src.agent.tools.list_files import _list_files_impl
from tests.test_helper import create_test_repo


def test_list_files() -> None:
    with create_test_repo() as repo_path:
        result = _list_files_impl(str(repo_path))

        assert isinstance(result, list)
        assert "file1.py" in result
        assert "file3.py" in result
        assert len(result) == 3


def test_list_files_truncation() -> None:
    """Test that list_files truncates results when max_files is exceeded."""
    with create_test_repo() as repo_path:
        # Request max of 2 files
        result = _list_files_impl(str(repo_path), max_files=2)

        assert isinstance(result, list)
        assert len(result) == 3  # 2 files + 1 truncation warning
        # Last item should be the truncation warning
        assert result[-1].startswith("[TRUNCATED:")
        assert "Showing 2 of 3 files" in result[-1]
