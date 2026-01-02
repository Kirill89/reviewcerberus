"""Primary review agent for expert mode (Stage 1).

This agent performs comprehensive code review and generates structured findings.
"""

from typing import Any

from ...config import RECURSION_LIMIT
from ..prompts import get_prompt
from ..token_usage import TokenUsage
from ..tools.changed_files import FileChange
from ..tools.read_file import ReadFile
from ..tools.search_in_files_locations import SearchInFilesLocations
from .agent_factory import create_expert_agent
from .schemas import PrimaryReviewContext, PrimaryReviewOutput
from .token_warning_injector import TokenWarningInjector


def run_primary_review(
    repo_path: str,
    target_branch: str,
    changed_files: list[FileChange],
    show_progress: bool = True,
    max_context_window: int = 200000,
) -> tuple[PrimaryReviewOutput, TokenUsage | None]:
    """Run the primary review agent (Stage 1).

    Args:
        repo_path: Path to git repository root
        target_branch: Target branch or commit to compare against
        changed_files: List of changed files
        show_progress: Whether to show progress messages
        max_context_window: Maximum context window size in tokens. Defaults to 200k.

    Returns:
        Tuple of (PrimaryReviewOutput, TokenUsage or None)
    """
    if show_progress:
        print("🔍 Stage 1: Performing initial review...")

    # Create token warning injector (used as both callback and middleware)
    token_warning_injector = TokenWarningInjector(
        max_context_window=max_context_window, recursion_limit=RECURSION_LIMIT
    )

    # Create read tracker to prevent duplicate file reads
    read_tracker = ReadFile()

    # Create search tracker to prevent duplicate searches
    search_tracker = SearchInFilesLocations()

    # Create agent
    system_prompt = get_prompt("expert_primary_review")
    agent = create_expert_agent(
        token_warning_injector=token_warning_injector,
        read_tracker=read_tracker,
        search_tracker=search_tracker,
        system_prompt=system_prompt,
        context_schema=PrimaryReviewContext,
        response_format=PrimaryReviewOutput,
    )

    # Create PrimaryReviewContext internally
    primary_context = PrimaryReviewContext(
        repo_path=repo_path,
        target_branch=target_branch,
        changed_files=changed_files,
    )

    config: dict[str, Any] = {
        "configurable": {
            "thread_id": "expert_primary",
        },
        "callbacks": [token_warning_injector],  # Track tokens via callback
    }

    # Invoke the agent with PrimaryReviewContext
    response = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Please review the code changes.",
                }
            ],
        },
        config=config,
        context=primary_context,
    )

    # Extract the structured output from response_format
    if "structured_response" not in response:
        raise ValueError("Primary review agent did not return structured output")

    primary_output: PrimaryReviewOutput = response["structured_response"]

    # Extract token usage
    token_usage = TokenUsage.from_response(response)

    if show_progress:
        print(f"✅ Stage 1: Found {primary_output.finding_count()} potential issues")

    return primary_output, token_usage
