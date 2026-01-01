"""Validation agent for expert mode (Stage 2).

This agent validates findings from Stage 1 to filter false positives.
"""

from typing import Any

from ..prompts import get_prompt
from ..token_usage import TokenUsage
from ..tools.changed_files import FileChange
from ..tools.read_file import ReadFile
from .agent_factory import create_expert_agent
from .schemas import PrimaryReviewOutput, ValidationContext, ValidationOutput
from .token_warning_injector import TokenWarningInjector


def run_validation(
    repo_path: str,
    target_branch: str,
    changed_files: list[FileChange],
    primary_output: PrimaryReviewOutput,
    show_progress: bool = True,
    max_context_window: int = 200000,
) -> tuple[ValidationOutput, TokenUsage | None]:
    """Run the validation agent (Stage 2).

    Args:
        repo_path: Path to git repository root
        target_branch: Target branch or commit to compare against
        changed_files: List of changed files
        primary_output: Output from Stage 1 containing findings to validate
        show_progress: Whether to show progress messages
        max_context_window: Maximum context window size in tokens. Defaults to 200k.

    Returns:
        Tuple of (ValidationOutput, TokenUsage or None)
    """
    if show_progress:
        print("🔍 Stage 2: Validating findings...")

    # Create token warning injector (used as both callback and middleware)
    token_warning_injector = TokenWarningInjector(max_context_window=max_context_window)

    # Create read tracker to prevent duplicate file reads
    read_tracker = ReadFile()

    # Create agent
    system_prompt = get_prompt("expert_validation")
    agent = create_expert_agent(
        token_warning_injector=token_warning_injector,
        read_tracker=read_tracker,
        system_prompt=system_prompt,
        context_schema=ValidationContext,
        response_format=ValidationOutput,
    )

    # Create ValidationContext with findings to validate
    validation_context = ValidationContext(
        repo_path=repo_path,
        target_branch=target_branch,
        changed_files=changed_files,
        findings_to_validate=primary_output.findings,
        changes_summary=primary_output.summary,
    )

    config: dict[str, Any] = {
        "configurable": {
            "thread_id": "expert_validation",
        },
        "callbacks": [token_warning_injector],  # Track tokens via callback
    }

    # Invoke the agent with ValidationContext
    response = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Please validate all {len(primary_output.findings)} findings provided in the context.",
                }
            ],
        },
        config=config,
        context=validation_context,
    )

    # Extract the structured output from response_format
    if "structured_response" not in response:
        raise ValueError("Validation agent did not return structured output")

    validation_output: ValidationOutput = response["structured_response"]

    # Verify we got validations for all findings
    if len(validation_output.findings) != len(primary_output.findings):
        raise ValueError(
            f"Validation count mismatch: expected {len(primary_output.findings)} "
            f"validations, got {len(validation_output.findings)}"
        )

    # Extract token usage
    token_usage = TokenUsage.from_response(response)

    if show_progress:
        confirmed = validation_output.confirmed_count()
        filtered = validation_output.filtered_count()
        print(f"✅ Stage 2: Confirmed {confirmed} findings, filtered {filtered}")

    return validation_output, token_usage
