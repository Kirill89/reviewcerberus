"""Verification agent runner."""

from typing import Any

from langchain.agents import create_agent

from ....config import RECURSION_LIMIT
from ...callbacks import RecursionTracker
from ...middleware import SummarizingMiddleware, ToolDeduplicationMiddleware
from ...model import model
from ...prompts import get_prompt
from ...schema import ContextWithFindings
from ...token_usage import TokenUsage, aggregate_token_usage
from ...tools import (
    changed_files,
    diff_file,
    get_commit_messages,
    list_files,
    read_file_part,
    search_in_files,
)
from ..schemas import SpecializedAgentOutput, VerificationAgentOutput
from .helpers import (
    add_ids_to_findings,
    filter_findings_by_ids,
    strip_confidence_scores,
)


async def run_verification_agent(
    agent_outputs: dict[str, SpecializedAgentOutput],
    repo_path: str,
    target_branch: str,
    changed_files_list: list,
) -> tuple[
    dict[str, SpecializedAgentOutput], TokenUsage | None, dict[str, int], list[str], int
]:
    """Run verification agent to filter false positives from specialized agent findings.

    Args:
        agent_outputs: Dictionary mapping agent names to their outputs
        repo_path: Absolute path to the git repository
        target_branch: Base branch to compare against
        changed_files_list: List of FileChange objects

    Returns:
        Tuple of (filtered agent outputs dict, token usage or None, recursion stats dict,
                  verification notes, removed issues count)
    """
    system_prompt = get_prompt("expert/verification_agent")

    # Append tool usage guidance
    tool_usage_guidance = get_prompt("tool_usage_efficiency")
    system_prompt = f"{system_prompt}\n\n{tool_usage_guidance}"

    # Step 1: Add IDs to all findings
    findings_with_ids = add_ids_to_findings(agent_outputs)

    # Step 2: Strip confidence scores to avoid bias
    agent_findings_stripped = strip_confidence_scores(findings_with_ids)

    # Count total issues/notes before filtering
    total_issues_before = sum(
        len(findings.get("issues", [])) for findings in findings_with_ids.values()
    )
    total_notes_before = sum(
        len(findings.get("notes", [])) for findings in findings_with_ids.values()
    )

    # Create context with agent findings (with IDs, without confidence scores)
    context_with_findings = ContextWithFindings(
        repo_path=repo_path,
        target_branch=target_branch,
        changed_files=changed_files_list,
        agent_findings=agent_findings_stripped,
        agent_name="verification",
    )

    # Create recursion tracker
    recursion_tracker = RecursionTracker(
        recursion_limit=RECURSION_LIMIT, agent_name="verification"
    )

    # Create verification agent with all tools
    agent: Any = create_agent(
        model=model,
        system_prompt=system_prompt,
        tools=[
            changed_files,
            get_commit_messages,
            diff_file,
            read_file_part,
            search_in_files,
            list_files,
        ],
        context_schema=ContextWithFindings,
        middleware=[
            ToolDeduplicationMiddleware(window_size=10),
            recursion_tracker,
            SummarizingMiddleware(),
        ],
        response_format=VerificationAgentOutput,
    )

    print("  Running verification agent to filter false positives...")

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Please verify all findings from the specialized agents and filter out false positives. Review each issue and note by its ID, and return only the IDs of legitimate findings. The agent findings with IDs are available in the context.",
                }
            ],
        },
        config={
            "recursion_limit": RECURSION_LIMIT,
            "callbacks": [recursion_tracker],
        },
        context=context_with_findings,
    )

    if "structured_response" not in result:
        raise ValueError("Verification agent did not return structured output")

    structured_output: VerificationAgentOutput = result["structured_response"]

    # Step 3: Filter findings by accepted IDs
    verified_agent_outputs = filter_findings_by_ids(
        findings_with_ids,
        structured_output.accepted_issue_ids,
        structured_output.accepted_note_ids,
    )

    # Calculate removed count
    total_issues_after = sum(
        len(output.issues) for output in verified_agent_outputs.values()
    )
    total_notes_after = sum(
        len(output.notes) for output in verified_agent_outputs.values()
    )
    removed_count = (total_issues_before - total_issues_after) + (
        total_notes_before - total_notes_after
    )

    # Aggregate token usage
    usage = None
    if "messages" in result:
        usage = aggregate_token_usage(result["messages"])

    # Get recursion tracker statistics
    stats = recursion_tracker.get_stats()

    return (
        verified_agent_outputs,
        usage,
        stats,
        structured_output.verification_notes,
        removed_count,
    )
