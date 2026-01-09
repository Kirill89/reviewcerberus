import fnmatch
import subprocess
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


def _list_files_impl(
    repo_path: str,
    directory: str = ".",
    pattern: str | None = None,
    max_files: int = 100,
) -> list[str]:
    """List files in repository."""
    result = subprocess.run(
        ["git", "-C", repo_path, "ls-tree", "-r", "--name-only", "HEAD", directory],
        capture_output=True,
        text=True,
        check=True,
    )

    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    if pattern:
        files = [f for f in files if fnmatch.fnmatch(f, pattern)]

    total_count = len(files)
    if total_count > max_files:
        files = files[:max_files]
        files.append(
            f"[TRUNCATED: Showing {max_files} of {total_count} files. "
            f"Use a more specific directory path or pattern to see other files.]"
        )

    return files


class ListFilesInput(BaseModel):
    """Input schema for list_files tool."""

    directory: str = Field(
        default=".",
        description="Directory to list files from (relative to repo root)",
    )
    pattern: str | None = Field(
        default=None,
        description="Optional glob pattern to filter files (e.g., '*.py')",
    )


class ListFilesTool(BaseTool):
    """Tool to list files in the repository or a specific directory."""

    name: str = "list_files"
    description: str = (
        "List files in the repository or a specific directory. "
        "Returns up to 100 files to avoid context explosion."
    )
    args_schema: type[BaseModel] = ListFilesInput

    repo_path: str

    def _run(
        self,
        directory: str = ".",
        pattern: str | None = None,
        **kwargs: Any,
    ) -> str:
        if pattern:
            print(f"🔧 list_files: {directory} ({pattern})")
        else:
            print(f"🔧 list_files: {directory}")

        try:
            files = _list_files_impl(self.repo_path, directory, pattern)
            return "\n".join(files)
        except Exception as e:
            print(f"   ✗ Error: {str(e)}")
            return f"Error listing files in {directory}: {str(e)}"
