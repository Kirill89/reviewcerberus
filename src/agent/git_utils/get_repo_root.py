"""Get the repository root directory."""

import subprocess


def get_repo_root(path: str | None = None) -> str:
    """Get the root directory of a git repository.

    Args:
        path: Optional path within the repository. If None, uses the current
            working directory.

    Returns:
        Absolute path to the repository root.

    Raises:
        subprocess.CalledProcessError: If the git command fails
            (e.g., not a git repository).
    """
    cmd = ["git", "rev-parse", "--show-toplevel"]
    if path:
        cmd = ["git", "-C", path, "rev-parse", "--show-toplevel"]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()
