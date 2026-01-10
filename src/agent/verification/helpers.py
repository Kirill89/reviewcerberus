"""Helper functions for the verification pipeline."""

from __future__ import annotations

from ..schema import ReviewIssue
from .schema import (
    IssueVerification,
    VerificationOutput,
    VerifiedReviewIssue,
)


def assign_issue_ids(issues: list[ReviewIssue]) -> dict[int, ReviewIssue]:
    """Step 0.5: Assign sequential IDs to issues.

    Args:
        issues: List of ReviewIssue from primary review

    Returns:
        Dictionary mapping issue ID (0-indexed) to ReviewIssue
    """
    return {idx: issue for idx, issue in enumerate(issues)}


def merge_verification_results(
    issues: dict[int, ReviewIssue],
    verification: VerificationOutput,
) -> list[VerifiedReviewIssue]:
    """Step 3.5: Merge verification scores into issues.

    Handles missing/hallucinated IDs gracefully by leaving confidence=None.

    Args:
        issues: Dictionary of {issue_id: ReviewIssue}
        verification: VerificationOutput with confidence scores

    Returns:
        List of VerifiedReviewIssue in original order
    """
    # Build lookup for verification results
    verification_by_id: dict[int, IssueVerification] = {}
    for v in verification.issues:
        verification_by_id[v.issue_id] = v

    # Create verified issues in original order
    verified_issues: list[VerifiedReviewIssue] = []
    for issue_id in sorted(issues.keys()):
        issue = issues[issue_id]
        verification_result = verification_by_id.get(issue_id)

        verified_issue = VerifiedReviewIssue(
            **issue.model_dump(),
            confidence=verification_result.confidence if verification_result else None,
            rationale=verification_result.rationale if verification_result else None,
        )

        verified_issues.append(verified_issue)

    return verified_issues
