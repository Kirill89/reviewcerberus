"""Get changed files between branches."""

import subprocess

from .types import FileChange


def get_changed_files(repo_path: str, target_branch: str) -> list[FileChange]:
    """Get list of changed files between target branch and HEAD.

    Args:
        repo_path: Absolute path to the git repository
        target_branch: Branch to compare against

    Returns:
        List of FileChange objects
    """
    result = subprocess.run(
        [
            "git",
            "-C",
            repo_path,
            "diff",
            "--name-status",
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
