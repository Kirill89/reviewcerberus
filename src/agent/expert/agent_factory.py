"""Helper for creating expert mode agents with common configuration."""

from typing import Any

from langchain.agents import create_agent

from ..model import model
from ..tools import (
    changed_files,
    diff_file,
    get_commit_messages,
    list_files,
)
from ..tools.read_file import ReadFile
from ..tools.search_in_files_locations import SearchInFilesLocations
from .token_warning_injector import TokenWarningInjector


def create_expert_agent(
    token_warning_injector: TokenWarningInjector,
    read_tracker: ReadFile,
    search_tracker: SearchInFilesLocations,
    system_prompt: str,
    context_schema: type,
    response_format: type,
) -> Any:
    """Create an expert mode agent with common configuration.

    Args:
        token_warning_injector: TokenWarningInjector instance to use as middleware
        read_tracker: ReadFile instance to prevent duplicate reads
        search_tracker: SearchInFilesLocations instance to prevent duplicate searches
        system_prompt: System prompt for the agent
        context_schema: Pydantic schema for agent context
        response_format: Pydantic schema for structured output

    Returns:
        Configured agent with structured output
    """
    return create_agent(
        model=model,
        system_prompt=system_prompt,
        tools=[
            changed_files,
            get_commit_messages,
            diff_file,
            read_tracker.create_tool(),
            search_tracker.create_tool(),
            list_files,
        ],
        context_schema=context_schema,
        checkpointer=None,  # No checkpointing for expert mode this iteration
        middleware=[token_warning_injector],  # Token tracking and warnings
        response_format=response_format,
    )
