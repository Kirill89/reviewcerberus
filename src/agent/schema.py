from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Context(BaseModel):
    repo_path: str = Field(description="Absolute path to the git repository")
    target_branch: str = Field(description="Base branch to compare against")


class IssueCategory(str, Enum):
    """Category of the code review issue."""

    LOGIC = "LOGIC"
    SECURITY = "SECURITY"
    ACCESS_CONTROL = "ACCESS_CONTROL"
    PERFORMANCE = "PERFORMANCE"
    QUALITY = "QUALITY"
    SIDE_EFFECTS = "SIDE_EFFECTS"
    TESTING = "TESTING"
    DOCUMENTATION = "DOCUMENTATION"


class IssueSeverity(str, Enum):
    """Severity level of the code review issue."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IssueLocation(BaseModel):
    """Location of an issue in the codebase."""

    filename: str = Field(description="Path to the file containing the issue")
    line: int | None = Field(
        default=None, description="Line number where the issue occurs, if applicable"
    )


class ReviewIssue(BaseModel):
    """A single issue found during code review."""

    title: str = Field(description="Short, descriptive title of the issue")
    category: IssueCategory = Field(description="Category of the issue")
    severity: IssueSeverity = Field(description="Severity level of the issue")
    location: list[IssueLocation] = Field(
        description="List of file locations where the issue occurs"
    )
    explanation: str = Field(
        description="Detailed explanation of the issue in markdown format, can include code samples"
    )
    suggested_fix: str = Field(
        description="Suggested fix in markdown format, can include code samples or instructions"
    )


class PrimaryReviewOutput(BaseModel):
    """Structured output from the primary review agent."""

    description: str = Field(
        description="High-level summary of changes in markdown format, including overview, key changes, and potentially risky areas"
    )
    issues: list[ReviewIssue] = Field(
        default_factory=list,
        description="List of issues found during the code review, ordered by severity",
    )
