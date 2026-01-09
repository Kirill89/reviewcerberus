import subprocess

from src.agent.tools.search_in_files import _search_impl
from tests.test_helper import create_test_repo


def test_search_in_files() -> None:
    with create_test_repo() as repo_path:
        result = _search_impl(str(repo_path), "def")

        assert isinstance(result, dict)
        assert len(result) > 0
        all_lines = [
            content for file_lines in result.values() for content in file_lines.values()
        ]
        assert any("def" in line for line in all_lines)


def test_search_in_files_returns_raw_lines() -> None:
    """Test that search returns raw untruncated lines."""
    with create_test_repo() as repo_path:
        long_line = "searchterm " + "a" * 1000
        test_file = repo_path / "longfile.py"
        test_file.write_text(long_line)

        subprocess.run(
            ["git", "-C", str(repo_path), "add", "."], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(repo_path), "commit", "-m", "Add long file"],
            check=True,
            capture_output=True,
        )

        result = _search_impl(str(repo_path), "searchterm")

        assert "longfile.py" in result
        file_lines = result["longfile.py"]
        assert any(len(content) > 500 for content in file_lines.values())
