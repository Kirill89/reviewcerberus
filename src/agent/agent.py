from typing import Any

from langchain.agents import create_agent

from .checkpointer import checkpointer
from .model import model
from .schema import Context
from .summarizing_middleware import SummarizingMiddleware
from .system import SYSTEM_PROMPT
from .tools import (
    changed_files,
    diff_file,
    get_commit_messages,
    list_files,
    read_file_part,
    search_in_files,
)


def create_review_agent(additional_instructions: str | None = None) -> Any:
    """Create an agent with optional additional instructions in the system prompt.

    Args:
        additional_instructions: Optional additional review guidelines to append
                                to the system prompt

    Returns:
        Configured agent instance with automatic in-loop summarization
    """
    system_prompt = SYSTEM_PROMPT

    if additional_instructions:
        system_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
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
