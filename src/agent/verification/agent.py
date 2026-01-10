"""LLM calls for the verification pipeline."""

from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from ...config import MAX_OUTPUT_TOKENS, MODEL_PROVIDER, VERIFY_MODEL_NAME
from ..formatting.format_verification import (
    format_issues_with_answers,
    format_issues_with_ids,
    format_questions_with_ids,
)
from ..prompts import get_prompt
from ..providers import PROVIDER_REGISTRY
from ..schema import ReviewIssue
from ..token_usage import TokenUsage
from .schema import (
    AnswersOutput,
    QuestionsOutput,
    VerificationOutput,
)


def get_verification_model() -> BaseChatModel:
    """Create model instance using VERIFY_MODEL_NAME config.

    Returns:
        Configured model instance for verification.

    Raises:
        ValueError: If MODEL_PROVIDER is not supported.
    """
    factory = PROVIDER_REGISTRY.get(MODEL_PROVIDER)

    if factory is None:
        supported = ", ".join(PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"Unsupported MODEL_PROVIDER: {MODEL_PROVIDER}. "
            f"Supported providers: {supported}"
        )

    model: BaseChatModel = factory(
        model_name=VERIFY_MODEL_NAME,
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    return model


def _invoke_agent(
    system_prompt: str,
    user_message: str,
    response_format: type,
) -> tuple[Any, TokenUsage | None]:
    """Invoke a verification agent and return structured output with token usage.

    Args:
        system_prompt: System prompt for the agent
        user_message: User message content
        response_format: Pydantic model for structured output

    Returns:
        Tuple of (structured output, TokenUsage or None)
    """
    model = get_verification_model()
    agent: Any = create_agent(
        model=model,
        system_prompt=system_prompt,
        tools=[],
        response_format=response_format,
    )

    response = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
        },
    )

    if "structured_response" not in response:
        raise ValueError("Verification agent did not return structured output")

    token_usage = TokenUsage.from_response(response)
    return response["structured_response"], token_usage


def generate_questions(
    system_prompt: str,
    user_message: str,
    file_context: str,
    issues: list[ReviewIssue],
) -> tuple[QuestionsOutput, TokenUsage | None]:
    """Step 1: Call LLM to generate falsification questions for each issue.

    Args:
        system_prompt: Original review system prompt
        user_message: Original review user message (diffs, commits)
        file_context: File content read during review (markdown)
        issues: List of issues to verify

    Returns:
        Tuple of (QuestionsOutput, TokenUsage or None)
    """
    prompt_template = get_prompt("verify_questions")
    prompt = prompt_template.format(
        original_system_prompt=system_prompt,
        user_message=user_message,
        file_context=file_context,
        issues_with_ids=format_issues_with_ids(issues),
    )

    return _invoke_agent(
        system_prompt=prompt,
        user_message="Generate verification questions for each issue.",
        response_format=QuestionsOutput,
    )


def answer_questions(
    system_prompt: str,
    user_message: str,
    file_context: str,
    questions: QuestionsOutput,
) -> tuple[AnswersOutput, TokenUsage | None]:
    """Step 2: Call LLM to answer verification questions from code context.

    Args:
        system_prompt: Original review system prompt
        user_message: Original review user message (diffs, commits)
        file_context: File content read during review (markdown)
        questions: Questions generated in step 1

    Returns:
        Tuple of (AnswersOutput, TokenUsage or None)
    """
    prompt_template = get_prompt("verify_answers")
    prompt = prompt_template.format(
        original_system_prompt=system_prompt,
        user_message=user_message,
        file_context=file_context,
        questions_with_ids=format_questions_with_ids(questions),
    )

    return _invoke_agent(
        system_prompt=prompt,
        user_message="Answer the verification questions based on the code.",
        response_format=AnswersOutput,
    )


def score_issues(
    issues: list[ReviewIssue],
    answers: AnswersOutput,
) -> tuple[VerificationOutput, TokenUsage | None]:
    """Step 3: Call LLM to score confidence 1-10 based on Q&A evidence.

    Args:
        issues: List of issues being verified
        answers: Answers from step 2

    Returns:
        Tuple of (VerificationOutput, TokenUsage or None)
    """
    prompt_template = get_prompt("verify_score")
    prompt = prompt_template.format(
        issues_with_answers=format_issues_with_answers(issues, answers),
    )

    return _invoke_agent(
        system_prompt=prompt,
        user_message="Score confidence for each issue based on the Q&A evidence.",
        response_format=VerificationOutput,
    )
