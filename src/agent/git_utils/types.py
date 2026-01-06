"""Type definitions for git utilities."""

from pydantic import BaseModel, Field


class FileChange(BaseModel):
    """Represents a changed file in a git diff."""

    path: str = Field(description="Relative path from repo root")
    change_type: str = Field(
        description="Type of change: added, modified, deleted, renamed"
    )
    old_path: str | None = Field(description="For renamed files", default=None)
    additions: int = Field(description="Number of lines added")
    deletions: int = Field(description="Number of lines deleted")


class CommitInfo(BaseModel):
    """Represents a commit in the git log."""

    sha: str
    author: str
    date: str
    message: str
