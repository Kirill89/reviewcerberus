import fnmatch
import subprocess

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from ..schema import Context


def _list_files_impl(
    repo_path: str, directory: str = ".", pattern: str | None = None
) -> list[str]:
    result = subprocess.run(
        ["git", "-C", repo_path, "ls-tree", "-r", "--name-only", "HEAD", directory],
        capture_output=True,
        text=True,
        check=True,
    )

    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    if pattern:
        files = [f for f in files if fnmatch.fnmatch(f, pattern)]

    return files


@tool
def list_files(
    runtime: ToolRuntime[Context], directory: str = ".", pattern: str | None = None
) -> list[str] | ToolMessage:
    """List files in the repository or a specific directory."""
    if pattern:
        print(f"🔧 [{runtime.context.agent_name}] list_files: {directory} ({pattern})")
    else:
        print(f"🔧 [{runtime.context.agent_name}] list_files: {directory}")
    try:
        return _list_files_impl(runtime.context.repo_path, directory, pattern)
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        return ToolMessage(
            content=f"Error listing files in {directory}: {str(e)}",
            tool_call_id=runtime.tool_call_id,
        )
