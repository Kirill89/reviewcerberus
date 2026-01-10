"""Formatting helpers for verification prompts."""

from __future__ import annotations

from ..schema import ReviewIssue
from ..verification.schema import AnswersOutput, IssueAnswers, QuestionsOutput
from .render_structured_output import render_issue


def format_issues_with_ids(issues: list[ReviewIssue]) -> str:
    """Format issues with IDs for prompt injection.

    Uses render_issue for consistent formatting, with 0-based indexing
    for issue ID correlation during verification.
    """
    parts = []
    for idx, issue in enumerate(issues):
        rendered = render_issue(issue, idx)
        parts.append(rendered)
    return "\n".join(parts)


def format_questions_with_ids(questions: QuestionsOutput) -> str:
    """Format questions with IDs for prompt injection."""
    lines = []
    for issue_q in questions.issues:
        lines.append(f"### Issue {issue_q.issue_id}")
        lines.append("")
        for i, q in enumerate(issue_q.questions, 1):
            lines.append(f"{i}. {q}")
        lines.append("")
    return "\n".join(lines)


def format_issues_with_answers(
    issues: list[ReviewIssue], answers: AnswersOutput
) -> str:
    """Format issues with their Q&A for scoring prompt."""
    lines = []
    answers_by_id: dict[int, IssueAnswers] = {ia.issue_id: ia for ia in answers.issues}

    for idx, issue in enumerate(issues):
        lines.append(f"### Issue {idx}: {issue.title}")
        lines.append("")
        lines.append(f"**Explanation:** {issue.explanation}")
        lines.append("")

        if idx in answers_by_id:
            lines.append("**Verification Q&A:**")
            lines.append("")
            for qa in answers_by_id[idx].answers:
                lines.append(f"- **Q:** {qa.question}")
                lines.append(f"  **A:** {qa.answer}")
            lines.append("")
        else:
            lines.append("*No Q&A available for this issue*")
            lines.append("")

    return "\n".join(lines)
