"""Get the current branch name."""

import subprocess


def get_current_branch(repo_path: str) -> str:
    """Get the current branch name of a git repository.

    Args:
        repo_path: Path to the git repository.

    Returns:
        The name of the current branch, or 'HEAD' if in detached HEAD state.

    Raises:
        subprocess.CalledProcessError: If the git command fails
            (e.g., not a git repository).
    """
    result = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()
