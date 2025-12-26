from typing import Any

import mdformat

from ..config import RECURSION_LIMIT
from .agent import create_review_agent
from .model import model
from .progress_callback_handler import ProgressCallbackHandler
from .prompts import get_prompt
from .schema import Context


def _format_review_content(raw_content: str) -> str:
    """Format and extract review content from AI response.

    Formats the markdown content with consistent styling (80-char wrap, numbered
    lists, GitHub Flavored Markdown) and extracts the review starting from the
    first markdown header, removing any meta-commentary.

    Args:
        raw_content: The raw content string from the AI response

    Returns:
        Formatted markdown content starting from the first header
    """
    formatted = mdformat.text(
        raw_content,
        options={
            "number": True,
            "wrap": 80,
        },
        extensions={
            "gfm",
        },
    )

    return "#" + formatted.split("#", 1)[1]


def summarize_review(
    review_content: str, show_progress: bool = True
) -> tuple[str, dict | None]:
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

    # Simple LLM call (not an agent)
    response = model.invoke(
        [{"role": "user", "content": f"{prompt}\n\n---\n\n{review_content}"}]
    )

    # Prepend summary to full review
    final_content = f"{response.content}\n\n---\n\n# Full Review\n\n{review_content}"

    # Format the entire combined content for uniform markdown
    final_content = _format_review_content(final_content)

    # Track token usage
    token_usage = None

    if hasattr(response, "usage_metadata") and response.usage_metadata:
        token_usage = {
            "input_tokens": response.usage_metadata.get("input_tokens", 0),
            "output_tokens": response.usage_metadata.get("output_tokens", 0),
        }

    return final_content, token_usage


def run_review(
    context: Context,
    mode: str = "full",
    show_progress: bool = True,
    additional_instructions: str | None = None,
) -> tuple[str, dict | None]:
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
        context=context,
    )

    token_usage = None
    if "messages" in response:
        final_message = response["messages"][-1]
        raw_content = (
            final_message.content
            if hasattr(final_message, "content")
            else str(final_message)
        )

        content = _format_review_content(raw_content)

        # Aggregate token usage across all AI messages
        total_output = 0
        cumulative_total = 0

        for msg in response["messages"]:
            if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                usage = msg.usage_metadata
                # Sum output tokens from each turn
                total_output += usage.get("output_tokens", 0)
                # Keep final cumulative total (increases each turn)
                cumulative_total = usage.get("total_tokens", 0)

        # Calculate total input as: cumulative_total - total_output
        total_input = cumulative_total - total_output

        if cumulative_total > 0:
            token_usage = {
                "total_input_tokens": total_input,
                "output_tokens": total_output,
                "total_tokens": cumulative_total,
            }
    else:
        content = str(response)

    return content, token_usage
