import pytest

from src.agent.tools.read_file_part import _read_file_impl
from tests.test_helper import create_test_repo


def test_read_file_part() -> None:
    with create_test_repo() as repo_path:
        result = _read_file_impl(str(repo_path), "file1.py", start_line=1, num_lines=2)

        assert "file1.py" in result.lines
        file_lines = result.lines["file1.py"]

        assert 1 in file_lines
        assert 2 in file_lines
        assert result.total_lines == 3
        assert "def hello():" in file_lines[1]


@pytest.mark.parametrize(
    ("contents", "expected"),
    [
        (b"# caf\xc3(\nreturn 42\n", "# caf\ufffd("),
        (b"# caf\xe9\nreturn 42\n", "# caf\ufffd"),
        ("# café\nreturn 42\n".encode("utf-8"), "# café"),
    ],
    ids=["invalid-utf8", "latin1", "valid-utf8"],
)
def test_read_file_handles_file_encodings(contents: bytes, expected: str) -> None:
    with create_test_repo({"legacy.py": contents}) as repo_path:
        result = _read_file_impl(str(repo_path), "legacy.py")
        assert result.lines == {"legacy.py": {1: expected, 2: "return 42"}}
        assert result.total_lines == 2
        assert (repo_path / "legacy.py").read_bytes() == contents
