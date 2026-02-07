"""Build review context message."""

from ..git_utils import FileChange, get_commit_messages, get_file_diff


def build_review_context(
    repo_path: str,
    target_branch: str,
    changed_files: list[FileChange],
    sast_findings: str | None = None,
) -> str:
    """Build the full review context message with commits, files, and diffs.

    Args:
        repo_path: Absolute path to the git repository
        target_branch: Branch to compare against
        changed_files: List of changed files
        sast_findings: Optional trimmed SAST findings JSON to append

    Returns:
        Formatted context string for the review
    """
    sections = ["Please review the code changes."]

    # Commits section
    commits = get_commit_messages(repo_path, target_branch)
    if commits:
        commit_lines = [
            f"- {c.sha[:7]} {c.message} ({c.author}, {c.date})" for c in commits
        ]
        sections.append("## Commits\n" + "\n".join(commit_lines))

    # Changed files section
    file_lines = []
    for f in changed_files:
        if f.old_path:
            file_lines.append(
                f"- {f.old_path} → {f.path} ({f.change_type}, +{f.additions}/-{f.deletions})"
            )
        else:
            file_lines.append(
                f"- {f.path} ({f.change_type}, +{f.additions}/-{f.deletions})"
            )
    sections.append("## Changed Files\n" + "\n".join(file_lines))

    # Diffs section
    diff_parts = []
    for f in changed_files:
        if f.change_type == "deleted":
            diff_parts.append(f"### {f.path}\n*File deleted*")
            continue

        diff = get_file_diff(repo_path, target_branch, f.path)
        if diff:
            diff_parts.append(f"### {f.path}\n```diff\n{diff}\n```")

    sections.append("## Diffs\n" + "\n\n".join(diff_parts))

    if sast_findings:
        sections.append("## SAST Findings\n" + sast_findings)

    return "\n\n".join(sections)
