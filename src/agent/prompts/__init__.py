"""Prompt loading utilities for the review agent."""

from pathlib import Path


def get_prompt(name: str) -> str:
    """Load a prompt by name.

    Maps mode names to filenames:
    - "full" → full_review.md
    - "summary" → summary_mode.md
    - "spaghetti" → spaghetti_code_detection.md
    - "security" → security_review.md

    For other prompts, uses direct names:
    - "context_summary" → context_summary.md

    Args:
        name: The prompt name or mode name

    Returns:
        The prompt content as a string

    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    # Map mode names to filenames
    mode_mapping = {
        "full": "full_review.md",
        "summary": "summary_mode.md",
        "spaghetti": "spaghetti_code_detection.md",
        "security": "security_review.md",
    }

    # Check if it's a mode name
    if name in mode_mapping:
        filename = mode_mapping[name]
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
