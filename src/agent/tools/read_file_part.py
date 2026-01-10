import subprocess
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..formatting.format_file_lines import FileLinesMap, format_file_lines
from .file_context import FileContext


class ReadFileResult(BaseModel):
    """Internal result from reading a file."""

    lines: FileLinesMap
    total_lines: int


def _read_file_impl(
    repo_path: str,
    file_path: str,
    start_line: int = 1,
    num_lines: int = 50,
) -> ReadFileResult:
    """Read lines from a file and return raw structure."""
    result = subprocess.run(
        ["git", "-C", repo_path, "show", f"HEAD:{file_path}"],
        capture_output=True,
        text=True,
        check=True,
    )

    all_lines = result.stdout.splitlines()
    total_lines = len(all_lines)

    end_line = min(start_line + num_lines - 1, total_lines)

    if start_line < 1 or start_line > total_lines:
        raise ValueError(
            f"Invalid start_line: {start_line} (file has {total_lines} lines)"
        )

    selected_lines = all_lines[start_line - 1 : end_line]

    lines: FileLinesMap = {
        file_path: {start_line + i: line for i, line in enumerate(selected_lines)}
    }

    return ReadFileResult(lines=lines, total_lines=total_lines)


class ReadFilePartInput(BaseModel):
    """Input schema for read_file_part tool."""

    file_path: str = Field(description="Path to the file relative to repository root")
    start_line: int = Field(
        default=1,
        description="Line number to start reading from (1-indexed)",
    )
    num_lines: int = Field(
        default=50,
        description="Number of lines to read",
    )


class ReadFilePartTool(BaseTool):
    """Tool to read a portion of a file starting from a specific line."""

    name: str = "read_file_part"
    description: str = (
        "Read a portion of a file starting from a specific line. "
        "Returns formatted content with line numbers. "
        "Examples: read_file_part(file_path='src/main.py', start_line=100, num_lines=50)"
    )
    args_schema: type[BaseModel] = ReadFilePartInput

    repo_path: str
    file_context: FileContext

    def _run(
        self,
        file_path: str,
        start_line: int = 1,
        num_lines: int = 50,
        **kwargs: Any,
    ) -> str:
        print(
            f"🔧 read_file_part: {file_path} (from line {start_line}, {num_lines} lines)"
        )

        try:
            result = _read_file_impl(self.repo_path, file_path, start_line, num_lines)

            # Track the lines in the file context
            self.file_context.update(result.lines)

            # Format for output with total lines in header
            return format_file_lines(
                result.lines,
                file_totals={file_path: result.total_lines},
            )
        except Exception as e:
            print(f"   ✗ Error: {str(e)}")
            return f"Error reading file {file_path}: {str(e)}"
