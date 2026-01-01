from src.agent.tools.search_in_files import _search_in_files_impl
from tests.test_helper import create_test_repo


def test_search_in_files_locations() -> None:
    """Test that search returns locations."""
    with create_test_repo() as repo_path:
        result = _search_in_files_impl(str(repo_path), "def")

        assert len(result) > 0
        assert result[0].file_path in ["file1.py", "file2.py", "file3.py"]
        assert result[0].line_number > 0
