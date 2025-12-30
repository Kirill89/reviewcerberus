"""Prompt loading utilities for the review agent."""

from pathlib import Path


def get_prompt(name: str) -> str:
    """Load a prompt by name.

    Modes:
    - "basic" → basic_mode.md (single comprehensive agent)
    - "expert" → Uses multiple specialized agents (implemented separately)

    Direct prompt names:
    - "context_summary" → context_summary.md
    - "executive_summary" → executive_summary.md

    Expert mode agents:
    - "expert/security_agent" → expert/security_agent.md
    - "expert/code_quality_agent" → expert/code_quality_agent.md
    - "expert/performance_agent" → expert/performance_agent.md
    - "expert/architecture_agent" → expert/architecture_agent.md
    - "expert/documentation_agent" → expert/documentation_agent.md
    - "expert/error_handling_agent" → expert/error_handling_agent.md
    - "expert/business_logic_agent" → expert/business_logic_agent.md
    - "expert/testing_agent" → expert/testing_agent.md
    - "expert/summary_agent" → expert/summary_agent.md

    Args:
        name: The prompt name or mode name

    Returns:
        The prompt content as a string

    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    # Map mode names to filenames
    mode_mapping = {
        "basic": "basic_mode.md",
    }

    # Check if it's a mode name
    if name in mode_mapping:
        filename = mode_mapping[name]
    elif "/" in name:
        # Expert mode agent (e.g., "expert/security_agent")
        filename = f"{name}.md"
    else:
        # Direct name (e.g., "context_summary")
        filename = f"{name}.md"

    # Get the prompts directory
    prompts_dir = Path(__file__).parent

    # Construct the full path
    prompt_path = prompts_dir / filename

    # Check if file exists
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    # Read and return the content
    with open(prompt_path, "r") as f:
        return f.read()
