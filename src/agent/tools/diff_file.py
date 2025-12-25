import re
import subprocess

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from pydantic import BaseModel

from ..schema import Context


class FileDiff(BaseModel):
    file_path: str
    diff: str
    additions: int
    deletions: int
    total_hunks: int
    returned_hunks: int
    start_hunk: int
    end_hunk: int


def _diff_file_impl(
    repo_path: str,
    target_branch: str,
    file_path: str,
    context_lines: int = 3,
    start_hunk: int = 1,
    end_hunk: int = 20,
) -> FileDiff:
    result = subprocess.run(
        [
            "git",
            "-C",
            repo_path,
            "diff",
            f"-U{context_lines}",
            f"{target_branch}...HEAD",
            "--",
            file_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    diff_text = result.stdout
    hunks = re.split(r"(?=^@@)", diff_text, flags=re.MULTILINE)[1:]
    total_hunks = len(hunks)

    if start_hunk < 1 or start_hunk > total_hunks:
        start_hunk = 1
    if end_hunk > total_hunks:
        end_hunk = total_hunks

    selected_hunks = hunks[start_hunk - 1 : end_hunk]
    diff_header = diff_text.split("@@")[0] if "@@" in diff_text else ""
    selected_diff = diff_header + "".join(selected_hunks)

    additions = diff_text.count("\n+") - diff_text.count("\n+++")
    deletions = diff_text.count("\n-") - diff_text.count("\n---")

    return FileDiff(
        file_path=file_path,
        diff=selected_diff,
        additions=additions,
        deletions=deletions,
        total_hunks=total_hunks,
        returned_hunks=len(selected_hunks),
        start_hunk=start_hunk,
        end_hunk=end_hunk,
    )


@tool
def diff_file(
    runtime: ToolRuntime[Context],
    file_path: str,
    context_lines: int = 3,
    start_hunk: int = 1,
    end_hunk: int = 20,
) -> FileDiff | ToolMessage:
    """Show git diff for a specific file between target branch and current branch (HEAD)."""
    print(f"🔧 diff_file: {file_path} (hunks {start_hunk}-{end_hunk})")

    try:
        return _diff_file_impl(
            runtime.context.repo_path,
            runtime.context.target_branch,
            file_path,
            context_lines,
            start_hunk,
            end_hunk,
        )
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        return ToolMessage(
            content=f"Error getting diff for {file_path}: {str(e)}",
            tool_call_id=runtime.tool_call_id,
        )
