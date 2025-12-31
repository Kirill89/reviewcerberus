import subprocess

from src.agent.tools.search_in_files import _search_in_files_impl
from tests.test_helper import create_test_repo


def test_search_in_files() -> None:
    with create_test_repo() as repo_path:
        result = _search_in_files_impl(str(repo_path), "def")

        assert isinstance(result, list)
        assert len(result) > 0
        assert any("def" in m.line_content for m in result)


def test_search_in_files_truncates_long_lines() -> None:
    """Test that very long lines are truncated to prevent context explosion."""
    with create_test_repo() as repo_path:
        # Create a file with a very long line (simulating minified code)
        # Put search term at the beginning so it's not truncated
        long_line = "very long line: " + "a" * 1000
        test_file = repo_path / "minified.js"
        test_file.write_text(long_line)

        # Commit the file
        subprocess.run(
            ["git", "-C", str(repo_path), "add", "."], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(repo_path), "commit", "-m", "Add minified file"],
            check=True,
            capture_output=True,
        )

        # Search for pattern in the long line
        result = _search_in_files_impl(str(repo_path), "very long", max_line_length=300)

        assert len(result) > 0
        match = result[0]

        # Verify line was truncated (300 chars + 29 char truncation message)
        assert len(match.line_content) == 329
        assert "[truncated due to line size]" in match.line_content
        assert "very long" in match.line_content  # Search term is at the start
