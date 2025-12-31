import fnmatch
import subprocess

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from ..schema import Context


def _list_files_impl(
    repo_path: str,
    directory: str = ".",
    pattern: str | None = None,
    max_files: int = 100,
) -> list[str]:
    """List files in repository.

    Returns up to max_files to avoid context explosion. If truncated,
    the last item in the list will be a warning message.
    """
    result = subprocess.run(
        ["git", "-C", repo_path, "ls-tree", "-r", "--name-only", "HEAD", directory],
        capture_output=True,
        text=True,
        check=True,
    )

    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    if pattern:
        files = [f for f in files if fnmatch.fnmatch(f, pattern)]

    # Truncate if too many files
    total_count = len(files)
    if total_count > max_files:
        files = files[:max_files]
        files.append(
            f"[TRUNCATED: Showing {max_files} of {total_count} files. "
            f"Use a more specific directory path or pattern to see other files.]"
        )

    return files


@tool
def list_files(
    runtime: ToolRuntime[Context], directory: str = ".", pattern: str | None = None
) -> list[str] | ToolMessage:
    """List files in the repository or a specific directory.

    Returns up to 100 files to avoid context explosion. If the directory
    contains more files, results will be truncated with a warning message
    as the last item in the list.
    """
    if pattern:
        print(f"🔧 list_files: {directory} ({pattern})")
    else:
        print(f"🔧 list_files: {directory}")
    try:
        return _list_files_impl(runtime.context.repo_path, directory, pattern)
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        return ToolMessage(
            content=f"Error listing files in {directory}: {str(e)}",
            tool_call_id=runtime.tool_call_id,
        )
