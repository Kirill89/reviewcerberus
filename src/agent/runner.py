from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from ..config import RECURSION_LIMIT
from .agent import create_review_agent
from .formatting import build_review_context
from .git_utils import FileChange
from .progress_callback_handler import ProgressCallbackHandler
from .recursion_guard import RecursionGuard
from .schema import Context, PrimaryReviewOutput
from .token_usage import TokenUsage


def run_review(
    repo_path: str,
    target_branch: str,
    changed_files: list[FileChange],
    show_progress: bool = True,
    additional_instructions: str | None = None,
) -> tuple[PrimaryReviewOutput, TokenUsage | None]:
    """Run the code review agent and return structured output.

    Args:
        repo_path: Path to the git repository
        target_branch: Target branch to compare against
        changed_files: List of changed files to review
        show_progress: Whether to show progress messages
        additional_instructions: Optional additional review guidelines

    Returns:
        Tuple of (PrimaryReviewOutput, TokenUsage or None)
    """
    context = Context(
        repo_path=repo_path,
        target_branch=target_branch,
    )

    # Build the review context with all diffs and commit messages
    user_message = build_review_context(repo_path, target_branch, changed_files)

    # Create recursion guard - used as both middleware and callback
    recursion_guard = RecursionGuard()

    # Create agent with recursion guard in middleware
    agent = create_review_agent(
        recursion_guard=recursion_guard,
        additional_instructions=additional_instructions,
    )

    # Add recursion guard to callbacks so it can track steps
    callbacks: list[BaseCallbackHandler] = [recursion_guard]
    if show_progress:
        callbacks.append(ProgressCallbackHandler())

    config: dict[str, Any] = {
        "configurable": {
            "thread_id": "1",
        },
        "callbacks": callbacks,
        "recursion_limit": RECURSION_LIMIT,
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

    return primary_output, token_usage
