"""Specialized agent runner."""

from typing import Any

from langchain.agents import create_agent

from ....config import RECURSION_LIMIT
from ...callbacks import RecursionTracker
from ...middleware import SummarizingMiddleware, ToolDeduplicationMiddleware
from ...model import model
from ...prompts import get_prompt
from ...schema import Context
from ...token_usage import TokenUsage, aggregate_token_usage
from ...tools import (
    changed_files,
    diff_file,
    get_commit_messages,
    list_files,
    read_file_part,
    search_in_files,
)
from ..schemas import SpecializedAgentOutput


async def run_specialized_agent(
    agent_name: str,
    prompt_path: str,
    repo_path: str,
    target_branch: str,
    changed_files_list: list,
) -> tuple[SpecializedAgentOutput, TokenUsage | None, dict[str, int]]:
    """Run a single specialized agent.

    Args:
        agent_name: Name of the agent (for logging)
        prompt_path: Path to the agent's prompt
        repo_path: Absolute path to the git repository
        target_branch: Base branch to compare against
        changed_files_list: List of FileChange objects

    Returns:
        Tuple of (structured output from the agent, token usage dict or None, stats dict)

    Raises:
        Exception: If agent fails
    """
    system_prompt = get_prompt(prompt_path)
    tool_usage_guidance = get_prompt("tool_usage_efficiency")
    system_prompt = f"{system_prompt}\n\n{tool_usage_guidance}"

    # Create recursion tracker (serves as both callback and middleware)
    recursion_tracker = RecursionTracker(
        recursion_limit=RECURSION_LIMIT, agent_name=agent_name
    )

    # Create agent with deduplication, recursion tracking, and summarizing middleware
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
        context_schema=Context,
        middleware=[
            ToolDeduplicationMiddleware(window_size=10),
            recursion_tracker,  # As middleware: injects warnings
            SummarizingMiddleware(),
        ],
        response_format=SpecializedAgentOutput,
    )

    print(f"  Running {agent_name} agent...")

    # Create context with agent name for tracking
    agent_context = Context(
        repo_path=repo_path,
        target_branch=target_branch,
        changed_files=changed_files_list,
        agent_name=agent_name,
    )

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Please analyze the code changes and provide your findings.",
                }
            ],
        },
        config={
            "recursion_limit": RECURSION_LIMIT,
            "callbacks": [recursion_tracker],  # As callback: tracks steps
        },
        context=agent_context,
    )

    if "structured_response" not in result:
        raise ValueError(f"Agent {agent_name} did not return structured output")

    structured_output: SpecializedAgentOutput = result["structured_response"]

    # Aggregate token usage across all AI messages
    usage = None
    if "messages" in result:
        usage = aggregate_token_usage(result["messages"])

    # Get recursion tracker statistics
    stats = recursion_tracker.get_stats()

    return structured_output, usage, stats
