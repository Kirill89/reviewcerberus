"""Tests for render_structured_output module."""

from src.agent.formatting.render_structured_output import (
    _get_severity_emoji,
    _sort_issues,
    render_structured_output,
)
from src.agent.schema import (
    IssueCategory,
    IssueLocation,
    IssueSeverity,
    PrimaryReviewOutput,
    ReviewIssue,
)


def _make_issue(
    title: str = "Test Issue",
    severity: IssueSeverity = IssueSeverity.MEDIUM,
) -> ReviewIssue:
    """Helper to create ReviewIssue instances for testing."""
    return ReviewIssue(
        title=title,
        category=IssueCategory.LOGIC,
        severity=severity,
        location=[IssueLocation(filename="test.py", line=10)],
        explanation="Test explanation",
        suggested_fix="Test fix",
    )


def test_get_severity_emoji() -> None:
    assert _get_severity_emoji(IssueSeverity.CRITICAL) == "🔴"
    assert _get_severity_emoji(IssueSeverity.HIGH) == "🟠"
    assert _get_severity_emoji(IssueSeverity.MEDIUM) == "🟡"
    assert _get_severity_emoji(IssueSeverity.LOW) == "🟢"


def test_sort_issues_by_severity() -> None:
    issues = [
        _make_issue(title="Low", severity=IssueSeverity.LOW),
        _make_issue(title="Critical", severity=IssueSeverity.CRITICAL),
        _make_issue(title="High", severity=IssueSeverity.HIGH),
    ]
    sorted_issues = _sort_issues(issues)

    assert sorted_issues[0].severity == IssueSeverity.CRITICAL
    assert sorted_issues[1].severity == IssueSeverity.HIGH
    assert sorted_issues[2].severity == IssueSeverity.LOW


def test_render_structured_output_with_issues() -> None:
    output = PrimaryReviewOutput(
        description="Summary of changes.",
        issues=[
            _make_issue(title="Bug Found", severity=IssueSeverity.HIGH),
        ],
    )
    result = render_structured_output(output)

    assert "# Code Review" in result
    assert "## Summary" in result
    assert "Summary of changes." in result
    assert "## Issues Summary" in result
    assert "Bug Found" in result
    assert "🟠 HIGH" in result


def test_render_structured_output_no_issues() -> None:
    output = PrimaryReviewOutput(
        description="All good.",
        issues=[],
    )
    result = render_structured_output(output)

    assert "No issues found during the review. ✅" in result
