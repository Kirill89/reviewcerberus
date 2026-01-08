"""Get the repository root directory."""

import subprocess


def get_repo_root(path: str | None = None) -> str:
    cmd = ["git", "rev-parse", "--show-toplevel"]
    if path:
        cmd = ["git", "-C", path, "rev-parse", "--show-toplevel"]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()
