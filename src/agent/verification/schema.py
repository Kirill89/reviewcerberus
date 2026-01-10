"""Pydantic models for the verification pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..schema import ReviewIssue


class IssueQuestions(BaseModel):
    """Step 1 output: verification questions for one issue."""

    issue_id: int = Field(description="ID of the issue being verified")
    questions: list[str] = Field(
        description="Falsification questions for this issue (max 10)"
    )


class QuestionsOutput(BaseModel):
    """Step 1 structured output wrapper."""

    issues: list[IssueQuestions] = Field(
        description="List of verification questions for each issue"
    )


class QuestionAnswer(BaseModel):
    """Single Q&A pair."""

    question: str = Field(description="The verification question")
    answer: str = Field(description="Factual answer based on code evidence")


class IssueAnswers(BaseModel):
    """Step 2 output: answers for one issue."""

    issue_id: int = Field(description="ID of the issue being verified")
    answers: list[QuestionAnswer] = Field(
        description="Answers to the verification questions"
    )


class AnswersOutput(BaseModel):
    """Step 2 structured output wrapper."""

    issues: list[IssueAnswers] = Field(description="List of answers for each issue")


class IssueVerification(BaseModel):
    """Step 3 output: confidence score for one issue."""

    issue_id: int = Field(description="ID of the issue being verified")
    confidence: int = Field(
        description="Confidence score from 1 (likely false positive) to 10 (definitely valid)",
        ge=1,
        le=10,
    )
    rationale: str = Field(description="Brief explanation of the confidence score")


class VerificationOutput(BaseModel):
    """Step 3 structured output wrapper."""

    issues: list[IssueVerification] = Field(
        description="List of confidence scores for each issue"
    )


class VerifiedReviewIssue(ReviewIssue):
    """ReviewIssue extended with optional verification results."""

    confidence: int | None = Field(
        default=None,
        description="Confidence score 1-10, None if verification failed/skipped",
    )
    rationale: str | None = Field(
        default=None,
        description="Verification rationale, None if verification failed/skipped",
    )


class VerifiedReviewOutput(BaseModel):
    """Final output matching PrimaryReviewOutput structure but with verification."""

    description: str = Field(
        description="High-level summary of changes in markdown format"
    )
    issues: list[VerifiedReviewIssue] = Field(
        default_factory=list,
        description="List of verified issues with confidence scores",
    )
