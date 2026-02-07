from dataclasses import dataclass
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from .agent import create_review_agent
from .formatting import build_review_context
from .git_utils import FileChange
from .progress_callback_handler import ProgressCallbackHandler
from .prompts import build_review_system_prompt
from .schema import Context, PrimaryReviewOutput
from .token_usage import TokenUsage
from .tools import FileContext


@dataclass
class ReviewResult:
    """Result from run_review with all data needed for verification."""

    output: PrimaryReviewOutput
    token_usage: TokenUsage | None
    file_context: FileContext
    user_message: str
    system_prompt: str


def run_review(
    repo_path: str,
    target_branch: str,
    changed_files: list[FileChange],
    show_progress: bool = True,
    additional_instructions: str | None = None,
    sast_findings: str | None = None,
) -> ReviewResult:
    """Run the code review agent and return structured output.

    Args:
        repo_path: Path to the git repository
        target_branch: Target branch to compare against
        changed_files: List of changed files to review
        show_progress: Whether to show progress messages
        additional_instructions: Optional additional review guidelines
        sast_findings: Optional trimmed SAST findings JSON to include in context

    Returns:
        ReviewResult containing output, token usage, and context for verification
    """
    context = Context(
        repo_path=repo_path,
        target_branch=target_branch,
    )

    # Build the review context with all diffs and commit messages
    user_message = build_review_context(
        repo_path, target_branch, changed_files, sast_findings
    )

    # Build system prompt
    include_sast = sast_findings is not None
    system_prompt = build_review_system_prompt(
        additional_instructions, include_sast_guidance=include_sast
    )

    # Create agent
    agent, file_context = create_review_agent(
        repo_path=repo_path,
        additional_instructions=additional_instructions,
        include_sast_guidance=include_sast,
    )

    callbacks: list[BaseCallbackHandler] = []
    if show_progress:
        callbacks.append(ProgressCallbackHandler())

    config: dict[str, Any] = {
        "configurable": {
            "thread_id": "1",
        },
        "callbacks": callbacks,
    }

    response = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
        },
        config=config,
        context=context,
    )

    token_usage = TokenUsage.from_response(response)

    # Extract structured response
    if "structured_response" not in response:
        raise ValueError("Primary review agent did not return structured output")

    primary_output: PrimaryReviewOutput = response["structured_response"]

    return ReviewResult(
        output=primary_output,
        token_usage=token_usage,
        file_context=file_context,
        user_message=user_message,
        system_prompt=system_prompt,
    )
