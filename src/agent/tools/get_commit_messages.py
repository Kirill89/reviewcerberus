import subprocess

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from pydantic import BaseModel

from ..schema import Context


class CommitInfo(BaseModel):
    sha: str
    author: str
    date: str
    message: str


def _get_commit_messages_impl(
    repo_path: str, target_branch: str, max_commits: int = 20
) -> list[CommitInfo]:
    result = subprocess.run(
        [
            "git",
            "-C",
            repo_path,
            "log",
            f"{target_branch}..HEAD",
            "--format=%H|%an|%ad|%s",
            "--date=short",
            f"-{max_commits}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    commits = []
    for line in result.stdout.splitlines():
        if line.strip():
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append(
                    CommitInfo(
                        sha=parts[0], author=parts[1], date=parts[2], message=parts[3]
                    )
                )

    return commits


@tool
def get_commit_messages(
    runtime: ToolRuntime[Context], max_commits: int = 20
) -> list[CommitInfo] | ToolMessage:
    """Get commit messages between target branch and current branch (HEAD)."""
    print(f"🔧 [{runtime.context.agent_name}] get_commit_messages")
    try:
        return _get_commit_messages_impl(
            runtime.context.repo_path, runtime.context.target_branch, max_commits
        )
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        return ToolMessage(
            content=f"Error getting commit messages: {str(e)}",
            tool_call_id=runtime.tool_call_id,
        )
