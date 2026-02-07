from typing import Any

from langchain.agents import create_agent

from .checkpointer import checkpointer
from .middleware import init_agent_middleware
from .model import model
from .prompts import build_review_system_prompt
from .schema import Context, PrimaryReviewOutput
from .tools import (
    FileContext,
    ListFilesTool,
    ReadFilePartTool,
    SearchInFilesTool,
)


def create_review_agent(
    repo_path: str,
    additional_instructions: str | None = None,
    include_sast_guidance: bool = False,
) -> tuple[Any, FileContext]:
    """Create a review agent with optional additional instructions.

    Args:
        repo_path: Path to the git repository
        additional_instructions: Optional additional review guidelines to append
                                to the system prompt
        include_sast_guidance: Whether to include SAST skepticism guidance

    Returns:
        Tuple of (configured agent instance, FileContext used by the agent)
    """
    system_prompt = build_review_system_prompt(
        additional_instructions, include_sast_guidance
    )

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
        middleware=init_agent_middleware(include_summarizing=True),
        response_format=PrimaryReviewOutput,
    )

    return agent, file_context
