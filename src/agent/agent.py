from typing import Any

from langchain.agents import create_agent

from .checkpointer import checkpointer
from .model import model
from .prompts import get_prompt
from .schema import Context, PrimaryReviewOutput
from .summarizing_middleware import SummarizingMiddleware
from .tools import (
    list_files,
    read_file_part,
    search_in_files,
)


def create_review_agent(additional_instructions: str | None = None) -> Any:
    """Create a review agent with optional additional instructions.

    Args:
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
        ],
        response_format=PrimaryReviewOutput,
    )
