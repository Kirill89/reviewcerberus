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
