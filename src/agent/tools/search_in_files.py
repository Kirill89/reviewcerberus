import subprocess
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..formatting.format_file_lines import FileLinesMap, format_file_lines
from .file_context import FileContext


def _parse_git_grep_line(line: str) -> tuple[str, int, str] | None:
    """Parse a git grep output line.

    Git grep uses different separators:
    - HEAD:file:linenum:content for matching lines (: separator)
    - HEAD:file-linenum-content for context lines (- separator)

    Returns tuple of (file_path, line_num, content) or None if parse fails.
    """
    if not line.startswith("HEAD:"):
        return None

    rest = line[5:]

    # Try matching line format first (uses : separator)
    # Format: file:linenum:content
    if ":" in rest:
        parts = rest.split(":", 2)
        if len(parts) >= 3 and parts[1].isdigit():
            return (parts[0], int(parts[1]), parts[2])

    # Try context line format (uses - separator)
    # Format: file-linenum-content
    # Need to find the file path first, then parse linenum-content
    if "-" in rest:
        # Find the last occurrence of -linenum- pattern
        # We split from the right to handle filenames with dashes
        parts = rest.rsplit("-", 2)
        if len(parts) >= 3 and parts[1].isdigit():
            return (parts[0], int(parts[1]), parts[2])

    return None


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
    matches_count = 0

    for line in output_lines:
        if line.startswith("--"):
            continue

        parsed = _parse_git_grep_line(line)
        if parsed:
            file_path, line_num, content = parsed

            if file_path not in lines:
                lines[file_path] = {}

            # Only count actual matches (lines with : separator) for max_results
            if line.startswith("HEAD:") and f":{line_num}:" in line:
                matches_count += 1
                if matches_count > max_results:
                    break

            lines[file_path][line_num] = content

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
