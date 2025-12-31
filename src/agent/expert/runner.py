"""Multi-agent runner for expert review mode."""

import asyncio

from ...config import MAX_PARALLEL_AGENTS
from ..formatting import format_agent_statistics
from ..token_usage import TokenUsage
from .agents import run_specialized_agent, run_summary_agent, run_verification_agent
from .schemas import SpecializedAgentOutput

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

    # Run verification agent to filter false positives
    try:
        (
            verified_outputs,
            verification_usage,
            verification_stats,
            verification_notes,
            removed_count,
        ) = await run_verification_agent(
            agent_outputs,
            repo_path,
            target_branch,
            changed_files,
        )

        # Add verification stats
        agent_stats["verification"] = verification_stats

        if show_progress:
            print(
                f"✓ Verification agent completed (filtered {removed_count} false positives)"
            )
            print()

    except Exception as e:
        if show_progress:
            print(f"\n❌ Verification agent failed: {str(e)}")
        raise

    # Run summary agent with VERIFIED findings
    try:
        review_content, summary_usage, summary_stats = await run_summary_agent(
            verified_outputs,
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

    # Add verification agent usage
    if verification_usage:
        total_usage = total_usage + verification_usage

    # Add summary agent usage
    if summary_usage:
        total_usage = total_usage + summary_usage

    # Append verification notes section
    verification_section = "\n\n---\n\n## Verification Agent Notes\n\n"
    if verification_notes:
        verification_section += "The following patterns of false positives were identified and filtered:\n\n"
        for note in verification_notes:
            verification_section += f"- {note}\n"
    else:
        verification_section += "No major patterns of false positives identified.\n"
    verification_section += f"\n**Total issues filtered:** {removed_count}\n"

    # Append agent statistics to the review
    stats_section = format_agent_statistics(agent_stats, verified_outputs)
    review_with_stats = review_content + verification_section + stats_section

    return review_with_stats, total_usage if total_usage.total_tokens > 0 else None
