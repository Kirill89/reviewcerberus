"""Render structured review output to markdown format."""

from ..schema import IssueSeverity, PrimaryReviewOutput, ReviewIssue

# Severity order for sorting (CRITICAL > HIGH > MEDIUM > LOW)
_SEVERITY_ORDER = {
    IssueSeverity.CRITICAL: 0,
    IssueSeverity.HIGH: 1,
    IssueSeverity.MEDIUM: 2,
    IssueSeverity.LOW: 3,
}


def _get_severity_emoji(severity: IssueSeverity) -> str:
    """Get emoji indicator for severity level."""
    return {
        IssueSeverity.CRITICAL: "🔴",
        IssueSeverity.HIGH: "🟠",
        IssueSeverity.MEDIUM: "🟡",
        IssueSeverity.LOW: "🟢",
    }.get(severity, "⚪")


def _sort_issues(issues: list[ReviewIssue]) -> list[ReviewIssue]:
    """Sort issues by severity (CRITICAL first, then HIGH, MEDIUM, LOW)."""
    return sorted(issues, key=lambda x: _SEVERITY_ORDER.get(x.severity, 99))


def _render_issues_summary_table(issues: list[ReviewIssue]) -> str:
    """Render a summary table of issues.

    Args:
        issues: List of issues (should be pre-sorted)

    Returns:
        Markdown table string
    """
    lines = [
        "## Issues Summary",
        "",
        "| # | Title | Category | Severity | Location |",
        "|---|-------|----------|----------|----------|",
    ]

    for idx, issue in enumerate(issues, 1):
        severity_emoji = _get_severity_emoji(issue.severity)
        # Get first file path for summary table
        file_path = issue.location[0].filename if issue.location else "-"
        if len(issue.location) > 1:
            file_path += f" (+{len(issue.location) - 1})"
        lines.append(
            f"| {idx} | {issue.title} | {issue.category.value} | "
            f"{severity_emoji} {issue.severity.value} | `{file_path}` |"
        )

    lines.append("")
    return "\n".join(lines)


def _render_issue(issue: ReviewIssue, index: int) -> str:
    """Render a single issue to markdown format."""
    severity_emoji = _get_severity_emoji(issue.severity)

    # Format locations
    locations_str = ", ".join(
        f"`{loc.filename}`" + (f" (line {loc.line})" if loc.line else "")
        for loc in issue.location
    )

    lines = [
        f"### {index}. {issue.title}",
        "",
        f"**Severity:** {severity_emoji} {issue.severity.value}  ",
        f"**Category:** {issue.category.value}  ",
        f"**Location:** {locations_str}",
        "",
        "#### Explanation",
        "",
        issue.explanation,
        "",
        "#### Suggested Fix",
        "",
        issue.suggested_fix,
        "",
    ]

    return "\n".join(lines)


def render_structured_output(output: PrimaryReviewOutput) -> str:
    """Render structured review output to markdown format.

    Args:
        output: The structured review output from the agent

    Returns:
        Formatted markdown string
    """
    sections = []

    # High-level summary section
    sections.append("# Code Review")
    sections.append("")
    sections.append("## Summary")
    sections.append("")
    sections.append(output.description)
    sections.append("")

    # Issues section
    if output.issues:
        sorted_issues = _sort_issues(output.issues)

        # Issues summary table
        sections.append(_render_issues_summary_table(sorted_issues))

        # Detailed issues section
        sections.append("## Issues Details")
        sections.append("")

        # Render each issue
        for idx, issue in enumerate(sorted_issues, 1):
            sections.append(_render_issue(issue, idx))
    else:
        sections.append("## Issues Summary")
        sections.append("")
        sections.append("No issues found during the review. ✅")
        sections.append("")

    return "\n".join(sections)
