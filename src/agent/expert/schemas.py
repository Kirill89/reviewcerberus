"""Pydantic schemas for expert mode two-stage review system.

All data structures are independent from the legacy codebase and can be adjusted freely.
"""

from enum import Enum

from pydantic import BaseModel, Field

from ..schema import Context


class PrimaryReviewContext(Context):
    """Context for primary review agent (Stage 1).

    Currently same as base Context, but defined separately for clarity
    and future extensibility.
    """


class Severity(str, Enum):
    """Severity levels for review findings."""

    CRITICAL = "critical"  # Security vulnerabilities, data loss, crashes
    HIGH = "high"  # Logic bugs, breaking changes, missing error handling
    MEDIUM = "medium"  # Code quality, performance, maintainability
    LOW = "low"  # Style, minor improvements, suggestions


class Location(BaseModel):
    """Code location for a finding."""

    filepath: str = Field(description="Path to the file relative to repo root")
    line_start: int = Field(description="Starting line number (1-indexed)")
    line_end: int = Field(description="Ending line number (1-indexed)")

    def format(self) -> str:
        """Format location as 'file:line_start-line_end'."""
        if self.line_start == self.line_end:
            return f"{self.filepath}:{self.line_start}"
        return f"{self.filepath}:{self.line_start}-{self.line_end}"


class ChangesSummary(BaseModel):
    """High-level summary of changes being reviewed."""

    changes_title: str = Field(description="Short title summarizing the changes")
    changes_description: str = Field(
        description="Detailed description of changes (markdown supported)"
    )


class ReviewFinding(BaseModel):
    """Individual issue identified by the primary review agent."""

    title: str = Field(description="Short title for the finding")
    description: str = Field(description="Detailed description (markdown supported)")
    location: list[Location] = Field(
        description="Code locations where this issue occurs"
    )
    recommendation: str = Field(
        description="Suggested fix or improvement (markdown supported)"
    )
    severity: Severity = Field(description="Severity level of the finding")


class ValidatedReviewFinding(ReviewFinding):
    """Review finding with validation results from Stage 2.

    The severity field may be adjusted by the validation agent from the original.
    """

    confirmed: bool = Field(description="True if finding is valid, False if rejected")
    validation_reason: str = Field(
        description="Explanation for confirmation/rejection (markdown supported)"
    )


class PrimaryReviewOutput(BaseModel):
    """Complete output from Stage 1 (primary review agent)."""

    summary: ChangesSummary = Field(description="High-level changes summary")
    findings: list[ReviewFinding] = Field(description="List of identified issues")

    def findings_by_severity(self, severity: Severity) -> list[ReviewFinding]:
        """Get all findings with a specific severity."""
        return [f for f in self.findings if f.severity == severity]

    def finding_count(self) -> int:
        """Get total number of findings."""
        return len(self.findings)


class ValidationContext(Context):
    """Extended context for validation agent with findings to validate."""

    findings_to_validate: list[ReviewFinding] = Field(
        description="Findings from primary review that need validation"
    )
    changes_summary: ChangesSummary = Field(
        description="High-level summary of changes for context"
    )


class ValidationOutput(BaseModel):
    """Complete output from Stage 2 (validation agent).

    Same structure as PrimaryReviewOutput but with validated findings.
    """

    findings: list[ValidatedReviewFinding] = Field(
        description="Validated findings (includes confirmation status and reasoning)"
    )

    def confirmed_count(self) -> int:
        """Get count of confirmed findings."""
        return sum(1 for f in self.findings if f.confirmed)

    def filtered_count(self) -> int:
        """Get count of filtered (rejected) findings."""
        return sum(1 for f in self.findings if not f.confirmed)

    def confirmation_rate(self) -> float:
        """Get percentage of confirmed findings."""
        if not self.findings:
            return 0.0
        return (self.confirmed_count() / len(self.findings)) * 100


class ExpertReviewResult(BaseModel):
    """Final output combining both stages with statistics."""

    # Original data
    summary: ChangesSummary
    all_findings: list[ValidatedReviewFinding]

    # Statistics
    total_findings: int
    confirmed_findings: int
    filtered_findings: int
    confirmation_rate: float

    def get_confirmed_findings(self) -> list[ValidatedReviewFinding]:
        """Get only confirmed findings."""
        return [f for f in self.all_findings if f.confirmed]

    def get_filtered_findings(self) -> list[ValidatedReviewFinding]:
        """Get only filtered findings."""
        return [f for f in self.all_findings if not f.confirmed]

    def confirmed_by_severity(self, severity: Severity) -> list[ValidatedReviewFinding]:
        """Get confirmed findings of a specific severity."""
        return [f for f in self.all_findings if f.confirmed and f.severity == severity]


def create_expert_review_result(
    primary_output: PrimaryReviewOutput, validation_output: ValidationOutput
) -> ExpertReviewResult:
    """Create final expert review result from both stages.

    Args:
        primary_output: Output from Stage 1
        validation_output: Output from Stage 2

    Returns:
        Complete expert review result with statistics
    """
    # Use validated findings from validation agent
    validated_findings = validation_output.findings

    confirmed_count = sum(1 for f in validated_findings if f.confirmed)
    filtered_count = len(validated_findings) - confirmed_count
    confirmation_rate = (
        (confirmed_count / len(validated_findings) * 100) if validated_findings else 0.0
    )

    return ExpertReviewResult(
        summary=primary_output.summary,
        all_findings=validated_findings,
        total_findings=len(validated_findings),
        confirmed_findings=confirmed_count,
        filtered_findings=filtered_count,
        confirmation_rate=confirmation_rate,
    )
