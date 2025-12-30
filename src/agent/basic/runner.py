"""Basic mode code review runner."""

from typing import Any

from ...config import RECURSION_LIMIT
from ..agent import create_review_agent
from ..callbacks import ProgressCallbackHandler
from ..formatting import format_review_content
from ..model import model
from ..prompts import get_prompt
from ..schema import Context
from ..token_usage import TokenUsage, aggregate_token_usage, extract_token_usage


async def summarize_review(
    review_content: str, show_progress: bool = True
) -> tuple[str, TokenUsage | None]:
    """Generate an executive summary of a code review and prepend it.

    Args:
        review_content: The full review markdown content
        show_progress: Whether to show progress messages

    Returns:
        Tuple of (content with summary prepended, token_usage dict)
    """
    if show_progress:
        print("📊 Generating executive summary...")

    prompt = get_prompt("executive_summary")

    # Simple LLM call (not an agent) - using async
    response = await model.ainvoke(
        [{"role": "user", "content": f"{prompt}\n\n---\n\n{review_content}"}]
    )

    # Prepend summary to full review
    final_content = f"{response.content}\n\n---\n\n# Full Review\n\n{review_content}"

    # Format the entire combined content for uniform markdown
    final_content = format_review_content(final_content)

    # Track token usage
    usage = extract_token_usage(response)
    return final_content, usage


async def run_review(
    repo_path: str,
    target_branch: str,
    changed_files: list,
    mode: str = "basic",
    show_progress: bool = True,
    additional_instructions: str | None = None,
) -> tuple[str, TokenUsage | None]:
    """Run basic mode code review with a single agent.

    Args:
        repo_path: Absolute path to the git repository
        target_branch: Base branch to compare against
        changed_files: List of FileChange objects
        mode: Review mode (basic or security)
        show_progress: Whether to show progress messages
        additional_instructions: Optional additional instructions for the agent

    Returns:
        Tuple of (review content as markdown, token usage dict or None)
    """
    # Create agent with additional instructions in system prompt for better effectiveness
    agent = create_review_agent(
        mode=mode, additional_instructions=additional_instructions
    )

    callbacks = []
    if show_progress:
        callbacks.append(ProgressCallbackHandler())

    config: dict[str, Any] = {
        "configurable": {
            "thread_id": "1",
        },
        "callbacks": callbacks,
        "recursion_limit": RECURSION_LIMIT,
    }

    # Create context with agent name for tracking
    review_context = Context(
        repo_path=repo_path,
        target_branch=target_branch,
        changed_files=changed_files,
        agent_name=mode,
    )

    response = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Please review the code changes.",
                }
            ],
        },
        config=config,
        context=review_context,
    )

    if "messages" in response:
        final_message = response["messages"][-1]
        raw_content = (
            final_message.content
            if hasattr(final_message, "content")
            else str(final_message)
        )

        content = format_review_content(raw_content)

        # Aggregate token usage across all AI messages
        usage = aggregate_token_usage(response["messages"])
    else:
        content = str(response)
        usage = TokenUsage()

    return content, usage if usage.total_tokens > 0 else None
