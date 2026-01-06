from __future__ import annotations

from pydantic import BaseModel, Field


class Context(BaseModel):
    repo_path: str = Field(description="Absolute path to the git repository")
    target_branch: str = Field(description="Base branch to compare against")
