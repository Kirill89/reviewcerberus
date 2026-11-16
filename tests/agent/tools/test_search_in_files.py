import subprocess

import pytest

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


def test_search_context_lines_have_correct_line_numbers() -> None:
    """Test that context lines (before and after match) have correct line numbers.

    Git grep uses different separators:
    - HEAD:file:linenum:content for matching lines
    - HEAD:file-linenum-content for context lines
    """
    with create_test_repo() as repo_path:
        # Create a file with known content
        test_file = repo_path / "context_test.py"
        test_file.write_text(
            "line1\n"  # line 1
            "line2\n"  # line 2
            "MATCH\n"  # line 3 - the match
            "line4\n"  # line 4
            "line5\n"  # line 5
        )

        subprocess.run(
            ["git", "-C", str(repo_path), "add", "."], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(repo_path), "commit", "-m", "Add test file"],
            check=True,
            capture_output=True,
        )

        # Search with 2 context lines
        result = _search_impl(str(repo_path), "MATCH", context_lines=2)

        assert "context_test.py" in result
        file_lines = result["context_test.py"]

        # Verify we have the correct line numbers for context lines
        # Line 1 (context before)
        assert 1 in file_lines, f"Line 1 missing. Got lines: {list(file_lines.keys())}"
        assert file_lines[1] == "line1"

        # Line 2 (context before)
        assert 2 in file_lines, f"Line 2 missing. Got lines: {list(file_lines.keys())}"
        assert file_lines[2] == "line2"

        # Line 3 (the match)
        assert 3 in file_lines, f"Line 3 missing. Got lines: {list(file_lines.keys())}"
        assert file_lines[3] == "MATCH"

        # Line 4 (context after)
        assert 4 in file_lines, f"Line 4 missing. Got lines: {list(file_lines.keys())}"
        assert file_lines[4] == "line4"

        # Line 5 (context after)
        assert 5 in file_lines, f"Line 5 missing. Got lines: {list(file_lines.keys())}"
        assert file_lines[5] == "line5"


@pytest.mark.parametrize(
    ("contents", "expected"),
    [
        (b"# caf\xc3(\nreturn 42\n", "# caf\ufffd("),
        (b"# caf\xe9\nreturn 42\n", "# caf\ufffd"),
        ("# café\nreturn 42\n".encode("utf-8"), "# café"),
    ],
    ids=["invalid-utf8", "latin1", "valid-utf8"],
)
def test_search_handles_file_encodings(contents: bytes, expected: str) -> None:
    with create_test_repo({"legacy.py": contents}) as repo_path:
        # The match is ASCII; the invalid bytes occur in a context line.
        result = _search_impl(str(repo_path), "return 42", file_pattern="legacy.py")
        assert result == {"legacy.py": {1: expected, 2: "return 42"}}
        assert (repo_path / "legacy.py").read_bytes() == contents
