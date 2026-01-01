"""Orchestrator for expert mode two-stage review process."""

from ..token_usage import TokenUsage
from ..tools.changed_files import FileChange
from .primary_agent import run_primary_review
from .renderer import render_expert_review
from .schemas import ValidationOutput, create_expert_review_result
from .validation_agent import run_validation


def run_expert_review(
    repo_path: str,
    target_branch: str,
    changed_files: list[FileChange],
    show_progress: bool = True,
    max_context_window: int = 200000,
) -> tuple[str, TokenUsage | None]:
    """Run the complete expert mode review (Stage 1 + Stage 2).

    Args:
        repo_path: Path to git repository root
        target_branch: Target branch or commit to compare against
        changed_files: List of changed files
        show_progress: Whether to show progress messages
        max_context_window: Maximum context window size in tokens

    Returns:
        Tuple of (formatted markdown content, combined TokenUsage or None)
    """
    # Stage 1: Primary Review
    primary_output, stage1_tokens = run_primary_review(
        repo_path,
        target_branch,
        changed_files,
        show_progress=show_progress,
        max_context_window=max_context_window,
    )

    # If no findings, skip validation
    if primary_output.finding_count() == 0:
        if show_progress:
            print("No issues found. Skipping validation stage.")

        # Create minimal result with empty validation output
        result = create_expert_review_result(
            primary_output,
            ValidationOutput(findings=[]),
        )

        # Render the output
        content = render_expert_review(result, stage1_tokens, None, show_progress)

        return content, stage1_tokens

    # Stage 2: Validation
    try:
        validation_output, stage2_tokens = run_validation(
            repo_path,
            target_branch,
            changed_files,
            primary_output,
            show_progress=show_progress,
            max_context_window=max_context_window,
        )
    except Exception as e:
        # If Stage 2 fails, fail entire review per plan requirements
        if show_progress:
            print(f"\n❌ Error: Stage 2 (validation) failed: {e}")
            print("Expert mode review failed. No partial results will be returned.")
        raise

    # Combine results using schema helper functions
    result = create_expert_review_result(primary_output, validation_output)

    # Combine token usage
    combined_tokens = None
    if stage1_tokens and stage2_tokens:
        combined_tokens = stage1_tokens + stage2_tokens
    elif stage1_tokens:
        combined_tokens = stage1_tokens

    # Render the markdown output and log statistics
    content = render_expert_review(
        result, stage1_tokens, stage2_tokens, show_progress=show_progress
    )

    return content, combined_tokens
