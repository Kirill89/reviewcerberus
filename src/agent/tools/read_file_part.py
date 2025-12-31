import subprocess

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from pydantic import BaseModel

from ..schema import Context
from .helpers import truncate_line


class FileContent(BaseModel):
    file_path: str
    content: str
    start_line: int
    end_line: int
    total_lines: int


def _read_file_part_impl(
    repo_path: str,
    file_path: str,
    start_line: int = 1,
    num_lines: int = 50,
    max_line_length: int = 500,
) -> FileContent:
    result = subprocess.run(
        ["git", "-C", repo_path, "show", f"HEAD:{file_path}"],
        capture_output=True,
        text=True,
        check=True,
    )

    lines = result.stdout.splitlines()
    total_lines = len(lines)

    # Calculate end_line from start_line + num_lines
    end_line = min(start_line + num_lines - 1, total_lines)

    if start_line < 1 or start_line > total_lines:
        raise ValueError(
            f"Invalid start_line: {start_line} (file has {total_lines} lines)"
        )

    selected_lines = lines[start_line - 1 : end_line]
    content = "\n".join(
        f"{i + start_line:6d}\t{truncate_line(line, max_line_length)}"
        for i, line in enumerate(selected_lines)
    )

    return FileContent(
        file_path=file_path,
        content=content,
        start_line=start_line,
        end_line=end_line,
        total_lines=total_lines,
    )


@tool
def read_file_part(
    runtime: ToolRuntime[Context],
    file_path: str,
    start_line: int = 1,
    num_lines: int = 50,
    max_line_length: int = 500,
) -> FileContent | ToolMessage:
    """Read a portion of a file starting from a specific line.

    Args:
        file_path: Path to the file relative to repository root
        start_line: Line number to start reading from (1-indexed). Defaults to 1 (beginning of file).
        num_lines: Number of lines to read. Defaults to 50. Will read fewer lines if near end of file.
        max_line_length: Maximum length for each line. Lines longer than this will be truncated. Defaults to 500.

    Returns:
        File content with line numbers for the specified range.

    Examples:
        - read_file_part("src/main.py", 100) - reads 50 lines starting from line 100
        - read_file_part("src/main.py", 100, 20) - reads 20 lines starting from line 100
        - read_file_part("src/main.py") - reads first 50 lines of the file

    Lines longer than max_line_length will be truncated to prevent massive outputs
    from minified code or generated files.
    """
    print(f"🔧 read_file_part: {file_path} (from line {start_line}, {num_lines} lines)")

    try:
        return _read_file_part_impl(
            runtime.context.repo_path, file_path, start_line, num_lines, max_line_length
        )
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        return ToolMessage(
            content=f"Error reading file {file_path}: {str(e)}",
            tool_call_id=runtime.tool_call_id,
        )
