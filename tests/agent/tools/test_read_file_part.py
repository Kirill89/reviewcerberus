from src.agent.tools.read_file_part import _read_file_part_impl
from tests.test_helper import create_test_repo


def test_read_file_part() -> None:
    with create_test_repo() as repo_path:
        result = _read_file_part_impl(
            str(repo_path), "file1.py", start_line=1, num_lines=2
        )

        assert result.file_path == "file1.py"
        assert result.start_line == 1
        assert result.end_line == 2
        assert result.total_lines == 3
        assert "def hello():" in result.content
