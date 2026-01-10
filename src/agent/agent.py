from typing import Any

from langchain.agents import create_agent

from .checkpointer import checkpointer
from .model import model
from .prompts import build_review_system_prompt
from .recursion_guard import RecursionGuard
from .schema import Context, PrimaryReviewOutput
from .summarizing_middleware import SummarizingMiddleware
from .tools import (
    FileContext,
    ListFilesTool,
    ReadFilePartTool,
    SearchInFilesTool,
)


def create_review_agent(
    repo_path: str,
    recursion_guard: RecursionGuard,
    additional_instructions: str | None = None,
) -> tuple[Any, FileContext]:
    """Create a review agent with optional additional instructions.

    Args:
        repo_path: Path to the git repository
        recursion_guard: RecursionGuard instance that tracks steps and forces
                        output when approaching recursion limit. Must also be
                        passed to invoke config callbacks.
        additional_instructions: Optional additional review guidelines to append
                                to the system prompt

    Returns:
        Tuple of (configured agent instance, FileContext used by the agent)
    """
    system_prompt = build_review_system_prompt(additional_instructions)

    # Create FileContext for tracking file content
    file_context = FileContext()

    # Create tools with repo_path and file_context
    tools = [
        ReadFilePartTool(repo_path=repo_path, file_context=file_context),
        SearchInFilesTool(repo_path=repo_path, file_context=file_context),
        ListFilesTool(repo_path=repo_path),
    ]

    agent = create_agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools,
        context_schema=Context,
        checkpointer=checkpointer,
        middleware=[
            SummarizingMiddleware(),
            recursion_guard,
        ],
        response_format=PrimaryReviewOutput,
    )

    return agent, file_context
