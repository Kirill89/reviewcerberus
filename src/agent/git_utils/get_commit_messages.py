"""Get commit messages between branches."""

import subprocess

from .types import CommitInfo


def get_commit_messages(
    repo_path: str, target_branch: str, max_commits: int = 50
) -> list[CommitInfo]:
    """Get commit messages between target branch and HEAD.

    Args:
        repo_path: Absolute path to the git repository
        target_branch: Branch to compare against
        max_commits: Maximum number of commits to return

    Returns:
        List of CommitInfo objects
    """
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
