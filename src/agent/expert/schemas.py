"""Pydantic schemas for multi-agent code review outputs."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Issue severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueLocation(BaseModel):
    """Location of an issue in the codebase."""

    file_path: str = Field(description="Path to the file containing the issue")
    line_start: int = Field(description="Starting line number", ge=1)
    line_end: int = Field(description="Ending line number", ge=1)


class AgentIssue(BaseModel):
    """Specific code issue found by an agent."""

    issue_type: str = Field(description="Category of the issue")
    severity: Severity = Field(description="Severity level of the issue")
    location: IssueLocation = Field(description="Location of the issue in code")
    description: str = Field(description="Clear explanation of the issue")
    recommendation: str = Field(
        description="Specific fix recommendation with code examples if helpful"
    )
    confidence_score: float = Field(
        description="Confidence in this finding (0.0-1.0)", ge=0.0, le=1.0
    )


class AgentNote(BaseModel):
    """General observation without specific file location."""

    note: str = Field(description="The observation or general finding")
    context: Optional[str] = Field(
        default=None, description="Optional additional context"
    )


class SpecializedAgentOutput(BaseModel):
    """Output from a specialized review agent."""

    issues: list[AgentIssue] = Field(
        default_factory=list, description="Specific code issues found"
    )
    notes: list[AgentNote] = Field(
        default_factory=list, description="General observations"
    )


class SummaryAgentOutput(BaseModel):
    """Output from the summary agent."""

    markdown_summary: str = Field(
        description="Complete markdown review synthesizing all agent findings"
    )
