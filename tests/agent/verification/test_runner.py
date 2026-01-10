"""Tests for verification runner."""

from typing import Any
from unittest.mock import MagicMock, patch

from src.agent.schema import (
    IssueCategory,
    IssueLocation,
    IssueSeverity,
    PrimaryReviewOutput,
    ReviewIssue,
)
from src.agent.tools import FileContext
from src.agent.verification.runner import run_verification
from src.agent.verification.schema import (
    AnswersOutput,
    IssueAnswers,
    IssueQuestions,
    IssueVerification,
    QuestionAnswer,
    QuestionsOutput,
    VerificationOutput,
)


def test_run_verification() -> None:
    """Test full verification pipeline with mocked model."""
    # Input
    primary_output = PrimaryReviewOutput(
        description="Test summary",
        issues=[
            ReviewIssue(
                title="Null pointer",
                category=IssueCategory.LOGIC,
                severity=IssueSeverity.HIGH,
                location=[IssueLocation(filename="main.py", line=10)],
                explanation="Variable may be null",
                suggested_fix="Add null check",
            ),
        ],
    )

    # Mock responses for each step
    questions_response = QuestionsOutput(
        issues=[
            IssueQuestions(issue_id=0, questions=["Is variable checked for null?"]),
        ]
    )
    answers_response = AnswersOutput(
        issues=[
            IssueAnswers(
                issue_id=0,
                answers=[
                    QuestionAnswer(
                        question="Is variable checked for null?",
                        answer="No null check exists",
                    )
                ],
            ),
        ]
    )
    verification_response = VerificationOutput(
        issues=[
            IssueVerification(issue_id=0, confidence=9, rationale="Issue confirmed"),
        ]
    )

    responses = [questions_response, answers_response, verification_response]
    call_index = 0

    def mock_invoke(input_dict: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        nonlocal call_index
        result = {"structured_response": responses[call_index], "messages": []}
        call_index += 1
        return result

    mock_agent = MagicMock()
    mock_agent.invoke.side_effect = mock_invoke

    with patch(
        "src.agent.verification.agent.create_agent", return_value=mock_agent
    ) as mock_create_agent:
        result, _ = run_verification(
            primary_output=primary_output,
            system_prompt="Review prompt",
            user_message="Diff content",
            file_context=FileContext(),
            repo_path="/test/repo",
            show_progress=False,
        )

    # Verify create_agent called 3 times with correct response_format
    assert mock_create_agent.call_count == 3

    # Step 1 (generate_questions): no tools
    assert mock_create_agent.call_args_list[0].kwargs["tools"] == []
    assert (
        mock_create_agent.call_args_list[0].kwargs["response_format"] == QuestionsOutput
    )

    # Step 2 (answer_questions): has tools
    assert len(mock_create_agent.call_args_list[1].kwargs["tools"]) == 3
    assert (
        mock_create_agent.call_args_list[1].kwargs["response_format"] == AnswersOutput
    )

    # Step 3 (score_issues): no tools
    assert mock_create_agent.call_args_list[2].kwargs["tools"] == []
    assert (
        mock_create_agent.call_args_list[2].kwargs["response_format"]
        == VerificationOutput
    )

    # Verify agent.invoke called 3 times
    assert mock_agent.invoke.call_count == 3

    # Verify result
    assert result.description == "Test summary"
    assert len(result.issues) == 1
    assert result.issues[0].title == "Null pointer"
    assert result.issues[0].confidence == 9
    assert result.issues[0].rationale == "Issue confirmed"
