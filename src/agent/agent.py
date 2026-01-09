from typing import Any

from langchain.agents import create_agent

from .checkpointer import checkpointer
from .model import model
from .prompts import get_prompt
from .recursion_guard import RecursionGuard
from .schema import Context, PrimaryReviewOutput
from .summarizing_middleware import SummarizingMiddleware
from .tools import (
    list_files,
    read_file_part,
    search_in_files,
)


def create_review_agent(
    recursion_guard: RecursionGuard,
    additional_instructions: str | None = None,
) -> Any:
    """Create a review agent with optional additional instructions.

    Args:
        recursion_guard: RecursionGuard instance that tracks steps and forces
                        output when approaching recursion limit. Must also be
                        passed to invoke config callbacks.
        additional_instructions: Optional additional review guidelines to append
                                to the system prompt

    Returns:
        Configured agent instance with automatic in-loop summarization
    """
    system_prompt = get_prompt("full_review")

    if additional_instructions:
        system_prompt = (
            f"{system_prompt}\n\n"
            f"## Additional Review Guidelines\n\n"
            f"{additional_instructions}"
        )

    return create_agent(
        model=model,
        system_prompt=system_prompt,
        tools=[
            read_file_part,
            search_in_files,
            list_files,
        ],
        context_schema=Context,
        checkpointer=checkpointer,
        middleware=[
            SummarizingMiddleware(),
            recursion_guard,
        ],
        response_format=PrimaryReviewOutput,
    )
