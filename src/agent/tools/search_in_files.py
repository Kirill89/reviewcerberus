import subprocess
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..formatting.format_file_lines import FileLinesMap, format_file_lines
from .file_context import FileContext


def _search_impl(
    repo_path: str,
    pattern: str,
    file_pattern: str | None = None,
    context_lines: int = 2,
    max_results: int = 50,
) -> FileLinesMap:
    """Search for patterns in files and return raw lines structure."""
    cmd = ["git", "-C", repo_path, "grep", "-n", f"-C{context_lines}", pattern, "HEAD"]
    if file_pattern:
        cmd.extend(["--", file_pattern])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 and result.returncode != 1:
        raise RuntimeError(f"Git grep failed: {result.stderr}")

    lines: FileLinesMap = {}
    output_lines = result.stdout.splitlines()

    current_file = None
    current_line_num = None
    matches_count = 0

    for line in output_lines:
        if line.startswith("--"):
            continue

        if line.startswith("HEAD:") and ":" in line[5:]:
            rest = line[5:]
            parts = rest.split(":", 2)
            if len(parts) >= 3:
                file_path = parts[0]
                line_num_str = parts[1]
                content = parts[2]

                if line_num_str.isdigit():
                    if current_file and current_line_num:
                        matches_count += 1
                        if matches_count >= max_results:
                            break

                    current_file = file_path
                    current_line_num = int(line_num_str)

                    if file_path not in lines:
                        lines[file_path] = {}
                    lines[file_path][current_line_num] = content
                else:
                    if current_file == file_path and current_file in lines:
                        last_line = max(lines[current_file].keys())
                        inferred_line_num = last_line + 1
                        lines[file_path][inferred_line_num] = content

    return lines


class SearchInFilesInput(BaseModel):
    """Input schema for search_in_files tool."""

    pattern: str = Field(description="Text pattern to search for")
    file_pattern: str | None = Field(
        default=None,
        description="Optional file pattern to filter search (e.g., '*.py')",
    )
    context_lines: int = Field(
        default=2,
        description="Number of context lines to show around matches",
    )
    max_results: int = Field(
        default=50,
        description="Maximum number of results to return",
    )


class SearchInFilesTool(BaseTool):
    """Tool to search for text patterns across files in the repository."""

    name: str = "search_in_files"
    description: str = (
        "Search for text patterns across files in the repository. "
        "Returns formatted search results with file paths, line numbers and context."
    )
    args_schema: type[BaseModel] = SearchInFilesInput

    repo_path: str
    file_context: FileContext

    def _run(
        self,
        pattern: str,
        file_pattern: str | None = None,
        context_lines: int = 2,
        max_results: int = 50,
        **kwargs: Any,
    ) -> str:
        if file_pattern:
            print(f"🔧 search_in_files: '{pattern}' in {file_pattern}")
        else:
            print(f"🔧 search_in_files: '{pattern}'")

        try:
            lines = _search_impl(
                self.repo_path,
                pattern,
                file_pattern,
                context_lines,
                max_results,
            )

            # Track the lines in the file context
            self.file_context.update(lines)

            if not lines:
                return "No matches found."

            return format_file_lines(lines)

        except Exception as e:
            print(f"   ✗ Error: {str(e)}")
            return f"Error searching for pattern {pattern}: {str(e)}"
