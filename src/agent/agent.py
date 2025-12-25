from typing import Any

from langchain.agents import create_agent

from .checkpointer import checkpointer
from .model import model
from .prompts import get_prompt
from .schema import Context
from .summarizing_middleware import SummarizingMiddleware
from .tools import (
    changed_files,
    diff_file,
    get_commit_messages,
    list_files,
    read_file_part,
    search_in_files,
)


def create_review_agent(
    mode: str = "full", additional_instructions: str | None = None
) -> Any:
    """Create an agent with optional mode and additional instructions.

    Args:
        mode: Review mode ("full" or "summary")
        additional_instructions: Optional additional review guidelines to append
                                to the system prompt

    Returns:
        Configured agent instance with automatic in-loop summarization
    """
    system_prompt = get_prompt(mode)

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
            changed_files,
            get_commit_messages,
            diff_file,
            read_file_part,
            search_in_files,
            list_files,
        ],
        context_schema=Context,
        checkpointer=checkpointer,
        middleware=[
            SummarizingMiddleware(),
        ],
    )
