from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


class Context(BaseModel):
    repo_path: str = Field(description="Absolute path to the git repository")
    target_branch: str = Field(description="Base branch to compare against")
    changed_files: list = Field(description="List of FileChange objects")
    agent_name: str = Field(
        description="Name of the current agent (for tracking tool calls)"
    )
    agent_findings: dict[str, Any] | None = Field(
        default=None,
        description="Structured findings from specialized agents (expert mode only)",
    )
