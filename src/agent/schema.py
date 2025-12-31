from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


class Context(BaseModel):
    """Base context for specialized agents."""

    repo_path: str = Field(description="Absolute path to the git repository")
    target_branch: str = Field(description="Base branch to compare against")
    changed_files: list = Field(description="List of FileChange objects")
    agent_name: str = Field(
        description="Name of the current agent (for tracking tool calls)"
    )


class ContextWithFindings(Context):
    """Extended context for verification and summary agents with agent findings."""

    agent_findings: dict[str, Any] = Field(
        description="Structured findings from specialized agents with IDs assigned"
    )
