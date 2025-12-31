"""Summary agent runner."""

from typing import Any

from langchain.agents import create_agent

from ....config import RECURSION_LIMIT
from ...callbacks import RecursionTracker
from ...formatting import format_review_content
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
from ..schemas import SpecializedAgentOutput, SummaryAgentOutput


async def run_summary_agent(
    agent_outputs: dict[str, SpecializedAgentOutput],
    repo_path: str,
    target_branch: str,
    changed_files_list: list,
    additional_instructions: str | None = None,
) -> tuple[str, TokenUsage | None, dict[str, int]]:
    """Run the summary agent to synthesize all specialized agent findings.

    Args:
        agent_outputs: Dictionary mapping agent names to their outputs
        repo_path: Absolute path to the git repository
        target_branch: Base branch to compare against
        changed_files_list: List of FileChange objects
        additional_instructions: Optional additional instructions for the review

    Returns:
        Tuple of (final markdown review content, token usage or None, recursion stats dict)
    """
    system_prompt = get_prompt("expert/summary_agent")

    if additional_instructions:
        system_prompt = (
            f"{system_prompt}\n\n"
            f"## Additional Review Guidelines\n\n"
            f"{additional_instructions}"
        )

    # Append tool usage guidance
    tool_usage_guidance = get_prompt("tool_usage_efficiency")
    system_prompt = f"{system_prompt}\n\n{tool_usage_guidance}"

    # Convert Pydantic models to dicts for context
    agent_findings_dict = {
        agent_name: output.model_dump() for agent_name, output in agent_outputs.items()
    }

    # Create context with agent findings and agent name for tracking
    context_with_findings = ContextWithFindings(
        repo_path=repo_path,
        target_branch=target_branch,
        changed_files=changed_files_list,
        agent_findings=agent_findings_dict,
        agent_name="summary",
    )

    # Create recursion tracker (serves as both callback and middleware)
    recursion_tracker = RecursionTracker(
        recursion_limit=RECURSION_LIMIT, agent_name="summary"
    )

    # Create summary agent with the bound model and summarizing middleware
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
            recursion_tracker,  # As middleware: injects warnings
            SummarizingMiddleware(),
        ],
        response_format=SummaryAgentOutput,
    )

    print("  Running summary agent to synthesize findings...")

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Please synthesize the findings from all specialized agents into a comprehensive code review. The agent findings are available in the context.",
                }
            ],
        },
        config={
            "recursion_limit": RECURSION_LIMIT,
            "callbacks": [recursion_tracker],  # As callback: tracks steps
        },
        context=context_with_findings,
    )

    if "structured_response" not in result:
        raise ValueError("Summary agent did not return structured output")

    structured_output: SummaryAgentOutput = result["structured_response"]

    # Aggregate token usage across all AI messages
    usage = None
    if "messages" in result:
        usage = aggregate_token_usage(result["messages"])

    # Get recursion tracker statistics
    stats = recursion_tracker.get_stats()

    # Format the markdown content with consistent styling
    formatted_summary = format_review_content(structured_output.markdown_summary)

    return formatted_summary, usage, stats
