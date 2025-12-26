import subprocess

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from pydantic import BaseModel, Field

from ..schema import Context


class FileChange(BaseModel):
    path: str = Field(description="Relative path from repo root")
    change_type: str = Field(
        description="Type of change: added, modified, deleted, renamed"
    )
    old_path: str | None = Field(description="For renamed files", default=None)
    additions: int = Field(description="Number of lines added")
    deletions: int = Field(description="Number of lines deleted")


def _changed_files_impl(repo_path: str, target_branch: str) -> list[FileChange]:
    result = subprocess.run(
        [
            "git",
            "-C",
            repo_path,
            "diff",
            "--name-status",
            "--numstat",
            f"{target_branch}...HEAD",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    numstat_result = subprocess.run(
        ["git", "-C", repo_path, "diff", "--numstat", f"{target_branch}...HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )

    # Parse numstat output, handling binary files (which show '-' instead of numbers)
    numstat_lines = {}
    for line in numstat_result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 3:
            continue

        # Binary files show '-' for additions/deletions
        additions = 0 if parts[0] == "-" else int(parts[0])
        deletions = 0 if parts[1] == "-" else int(parts[1])
        filepath = parts[2]

        numstat_lines[filepath] = (additions, deletions)

    changes = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        parts = line.split(maxsplit=2)
        if len(parts) < 2:
            continue

        status = parts[0]
        path = parts[1] if len(parts) == 2 else parts[2]

        change_type_map = {
            "A": "added",
            "M": "modified",
            "D": "deleted",
            "R": "renamed",
        }
        change_type = change_type_map.get(status[0], "modified")

        old_path = None
        if status.startswith("R") and len(parts) == 3:
            old_path = parts[1]
            path = parts[2]

        additions, deletions = numstat_lines.get(path, (0, 0))

        changes.append(
            FileChange(
                path=path,
                change_type=change_type,
                old_path=old_path,
                additions=additions,
                deletions=deletions,
            )
        )

    return changes


@tool
def changed_files(runtime: ToolRuntime[Context]) -> list[FileChange] | ToolMessage:
    """List all files that changed between target branch and current branch (HEAD)."""
    print(f"🔧 changed_files")
    try:
        return _changed_files_impl(
            runtime.context.repo_path, runtime.context.target_branch
        )
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        return ToolMessage(
            content=f"Error getting changed files: {str(e)}",
            tool_call_id=runtime.tool_call_id,
        )
