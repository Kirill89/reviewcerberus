"""Orchestration for the verification pipeline."""

from __future__ import annotations

import sys

from ..schema import PrimaryReviewOutput
from ..token_usage import TokenUsage
from ..tools import FileContext
from .agent import answer_questions, generate_questions, score_issues
from .helpers import assign_issue_ids, merge_verification_results
from .schema import VerifiedReviewOutput


def _show_progress(step: int, total: int = 3) -> None:
    """Display verification progress."""
    print(f"\r🔍 Verifying... (step {step}/{total})", end="", flush=True)


def run_verification(
    primary_output: PrimaryReviewOutput,
    system_prompt: str,
    user_message: str,
    file_context: FileContext,
    show_progress: bool = True,
) -> tuple[VerifiedReviewOutput, TokenUsage | None]:
    """Main entry point. Orchestrates steps 0.5->1->2->3->3.5.

    Skips verification if no issues. Shows progress: 🔍 Verifying... (step N/3).
    Returns VerifiedReviewOutput with confidence scores, or unverified for
    issues with hallucinated/missing IDs.

    Args:
        primary_output: Output from primary review agent
        system_prompt: Original review system prompt
        user_message: Original review user message (diffs, commits)
        file_context: FileContext with file content read during review
        show_progress: Whether to show progress messages

    Returns:
        Tuple of (VerifiedReviewOutput, TokenUsage or None)
    """
    # Skip verification if no issues
    if not primary_output.issues:
        return (
            VerifiedReviewOutput(
                description=primary_output.description,
                issues=[],
            ),
            None,
        )

    # Step 0.5: Assign IDs
    issues_by_id = assign_issue_ids(primary_output.issues)
    issues_list = list(issues_by_id.values())
    file_context_md = file_context.to_markdown()
    token_usage: TokenUsage | None = None

    # Step 1: Generate questions
    if show_progress:
        _show_progress(1)
    questions, usage1 = generate_questions(
        system_prompt=system_prompt,
        user_message=user_message,
        file_context=file_context_md,
        issues=issues_list,
    )
    if usage1:
        token_usage = usage1

    # Step 2: Answer questions
    if show_progress:
        _show_progress(2)
    answers, usage2 = answer_questions(
        system_prompt=system_prompt,
        user_message=user_message,
        file_context=file_context_md,
        questions=questions,
    )
    if usage2:
        token_usage = token_usage + usage2 if token_usage else usage2

    # Step 3: Score issues
    if show_progress:
        _show_progress(3)
    verification, usage3 = score_issues(
        issues=issues_list,
        answers=answers,
    )
    if usage3:
        token_usage = token_usage + usage3 if token_usage else usage3

    # Step 3.5: Merge results
    verified_issues = merge_verification_results(issues_by_id, verification)

    if show_progress:
        # Clear progress line and show completion
        print("\r" + " " * 40 + "\r", end="", file=sys.stdout)
        print("✓ Verification completed")

    return (
        VerifiedReviewOutput(
            description=primary_output.description,
            issues=verified_issues,
        ),
        token_usage,
    )
