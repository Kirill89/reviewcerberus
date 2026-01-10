"""Prompt loading utilities for the review agent."""

from pathlib import Path


def get_prompt(name: str) -> str:
    """Load a prompt by name.

    Args:
        name: The prompt name (without .md extension)

    Returns:
        The prompt content as a string

    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    # Get the prompts directory
    prompts_dir = Path(__file__).parent

    # Construct the full path
    prompt_path = prompts_dir / f"{name}.md"

    # Check if file exists
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    # Read and return the content
    with open(prompt_path, "r") as f:
        return f.read()
