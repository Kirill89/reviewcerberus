"""Get file diff between branches."""

import subprocess

from ...config import MAX_DIFF_PER_FILE


def get_file_diff(
    repo_path: str, target_branch: str, file_path: str, context_lines: int = 3
) -> str | None:
    """Get diff for a specific file, with truncation if too large.

    Args:
        repo_path: Absolute path to the git repository
        target_branch: Branch to compare against
        file_path: Path to the file relative to repo root
        context_lines: Number of context lines around changes

    Returns:
        Diff string (truncated if exceeds MAX_DIFF_PER_FILE), or None for binary files
    """
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

    # Check if this is a binary file
    if "Binary files" in diff_text or not diff_text.strip():
        return None

    # Truncate if too large
    if len(diff_text) > MAX_DIFF_PER_FILE:
        diff_text = (
            diff_text[:MAX_DIFF_PER_FILE]
            + f"\n\n[Diff truncated at {MAX_DIFF_PER_FILE} characters]"
        )

    return diff_text
