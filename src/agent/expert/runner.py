"""Multi-agent runner for expert review mode."""

import asyncio
from typing import Any

from langchain.agents import create_agent

from ...config import MAX_PARALLEL_AGENTS, RECURSION_LIMIT
from ..callbacks import RecursionTracker
from ..formatting import format_agent_statistics, format_review_content
from ..middleware import (
    SummarizingMiddleware,
    ToolDeduplicationMiddleware,
)
from ..model import model
from ..prompts import get_prompt
from ..schema import Context
from ..token_usage import TokenUsage, aggregate_token_usage

# Import all tools that agents will use
from ..tools import (
    changed_files,
    diff_file,
    get_commit_messages,
    list_files,
    read_file_part,
    search_in_files,
)
from .schemas import SpecializedAgentOutput, SummaryAgentOutput

# Agent names mapped to their prompt paths
SPECIALIZED_AGENTS = {
    "security": "expert/security_agent",
    "code_quality": "expert/code_quality_agent",
    "performance": "expert/performance_agent",
    "architecture": "expert/architecture_agent",
    "documentation": "expert/documentation_agent",
    "error_handling": "expert/error_handling_agent",
    "business_logic": "expert/business_logic_agent",
    "testing": "expert/testing_agent",
}


def get_enabled_agents(
    no_security: bool = False,
    no_code_quality: bool = False,
    no_performance: bool = False,
    no_architecture: bool = False,
    no_documentation: bool = False,
    no_error_handling: bool = False,
    no_business_logic: bool = False,
    no_testing: bool = False,
) -> dict[str, str]:
    """Get the list of enabled agents based on CLI flags.

    Args:
        no_security: Disable security agent
        no_code_quality: Disable code quality agent
        no_performance: Disable performance agent
        no_architecture: Disable architecture agent
        no_documentation: Disable documentation agent
        no_error_handling: Disable error handling agent
        no_business_logic: Disable business logic agent
        no_testing: Disable testing agent

    Returns:
        Dictionary mapping enabled agent names to their prompt paths
    """
    enabled = {}

    if not no_security:
        enabled["security"] = SPECIALIZED_AGENTS["security"]
    if not no_code_quality:
        enabled["code_quality"] = SPECIALIZED_AGENTS["code_quality"]
    if not no_performance:
        enabled["performance"] = SPECIALIZED_AGENTS["performance"]
    if not no_architecture:
        enabled["architecture"] = SPECIALIZED_AGENTS["architecture"]
    if not no_documentation:
        enabled["documentation"] = SPECIALIZED_AGENTS["documentation"]
    if not no_error_handling:
        enabled["error_handling"] = SPECIALIZED_AGENTS["error_handling"]
    if not no_business_logic:
        enabled["business_logic"] = SPECIALIZED_AGENTS["business_logic"]
    if not no_testing:
        enabled["testing"] = SPECIALIZED_AGENTS["testing"]

    return enabled


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
        Tuple of (structured output from the agent, token usage dict or None)

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
    context_with_findings = Context(
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
        context_schema=Context,
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


async def run_expert_review(
    repo_path: str,
    target_branch: str,
    changed_files: list,
    show_progress: bool = True,
    additional_instructions: str | None = None,
    no_security: bool = False,
    no_code_quality: bool = False,
    no_performance: bool = False,
    no_architecture: bool = False,
    no_documentation: bool = False,
    no_error_handling: bool = False,
    no_business_logic: bool = False,
    no_testing: bool = False,
) -> tuple[str, TokenUsage | None]:
    """Run expert review mode with multiple specialized agents in parallel.

    Args:
        repo_path: Absolute path to the git repository
        target_branch: Base branch to compare against
        changed_files: List of FileChange objects
        show_progress: Whether to show progress messages
        additional_instructions: Optional additional instructions for the review
        no_security: Disable security agent
        no_code_quality: Disable code quality agent
        no_performance: Disable performance agent
        no_architecture: Disable architecture agent
        no_documentation: Disable documentation agent
        no_error_handling: Disable error handling agent
        no_business_logic: Disable business logic agent
        no_testing: Disable testing agent

    Returns:
        Tuple of (review content as markdown, token usage dict or None)
    """
    if show_progress:
        print("🔬 Running expert mode review with specialized agents...")
        print()

    # Determine which agents are enabled
    enabled_agents = get_enabled_agents(
        no_security=no_security,
        no_code_quality=no_code_quality,
        no_performance=no_performance,
        no_architecture=no_architecture,
        no_documentation=no_documentation,
        no_error_handling=no_error_handling,
        no_business_logic=no_business_logic,
        no_testing=no_testing,
    )

    if show_progress:
        print(f"Enabled agents: {', '.join(enabled_agents.keys())}")
        print(f"Max parallel agents: {MAX_PARALLEL_AGENTS}")
        print()

    # Run all specialized agents with limited parallelism
    if show_progress:
        print("Running specialized agents...")

    # Create semaphore to limit concurrent execution
    semaphore = asyncio.Semaphore(MAX_PARALLEL_AGENTS)

    async def run_with_semaphore(
        name: str, prompt_path: str
    ) -> tuple[str, tuple[SpecializedAgentOutput, TokenUsage | None, dict[str, int]]]:
        """Run agent with semaphore to limit concurrency."""
        async with semaphore:
            result = await run_specialized_agent(
                name, prompt_path, repo_path, target_branch, changed_files
            )
            return name, result

    tasks = [
        run_with_semaphore(name, prompt_path)
        for name, prompt_path in enabled_agents.items()
    ]

    try:
        results = await asyncio.gather(*tasks)
    except Exception as e:
        if show_progress:
            print(f"\n❌ Expert review failed: {str(e)}")
        raise

    # Unpack results: separate outputs, usage, and stats
    agent_outputs = {}
    agent_usages = []
    agent_stats = {}
    for agent_name, (output, usage, stats) in results:
        agent_outputs[agent_name] = output
        agent_stats[agent_name] = stats
        if usage:
            agent_usages.append(usage)

    if show_progress:
        print(f"\n✓ All {len(agent_outputs)} specialized agents completed")
        print()

    # Run summary agent
    try:
        review_content, summary_usage, summary_stats = await run_summary_agent(
            agent_outputs,
            repo_path,
            target_branch,
            changed_files,
            additional_instructions,
        )
        # Add summary agent stats
        agent_stats["summary"] = summary_stats
    except Exception as e:
        if show_progress:
            print(f"\n❌ Summary agent failed: {str(e)}")
        raise

    if show_progress:
        print("✓ Summary agent completed")
        print()

    # Aggregate token usage from all agents
    total_usage = TokenUsage()

    # Sum up all specialized agent usage
    for usage in agent_usages:
        total_usage = total_usage + usage

    # Add summary agent usage
    if summary_usage:
        total_usage = total_usage + summary_usage

    # Append agent statistics to the review
    stats_section = format_agent_statistics(agent_stats, agent_outputs)
    review_with_stats = review_content + stats_section

    return review_with_stats, total_usage if total_usage.total_tokens > 0 else None
