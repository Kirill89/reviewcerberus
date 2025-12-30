"""Formatting utilities for review content."""

from typing import TYPE_CHECKING

import mdformat

if TYPE_CHECKING:
    from .expert.schemas import SpecializedAgentOutput


def format_review_content(raw_content: str) -> str:
    """Format and extract review content from AI response.

    Formats the markdown content with consistent styling (80-char wrap, numbered
    lists, GitHub Flavored Markdown) and extracts the review starting from the
    first markdown header, removing any meta-commentary.

    Args:
        raw_content: The raw content string from the AI response

    Returns:
        Formatted markdown content starting from the first header
    """
    formatted = mdformat.text(
        raw_content,
        options={
            "number": True,
            "wrap": 80,
        },
        extensions={
            "gfm",
        },
    )

    return "#" + formatted.split("#", 1)[1]


def format_agent_statistics(
    agent_stats: dict[str, dict[str, int]],
    agent_outputs: dict[str, "SpecializedAgentOutput"] | None = None,
) -> str:
    """Format agent execution statistics as markdown.

    Args:
        agent_stats: Dictionary mapping agent names to their stats
        agent_outputs: Optional dictionary mapping agent names to their outputs

    Returns:
        Formatted markdown section with agent information
    """
    lines = [
        "",
        "---",
        "",
        "## Agents",
        "",
    ]

    # Sort agents by name for consistent ordering (exclude summary)
    agent_names = sorted([name for name in agent_stats.keys() if name != "summary"])

    for agent_name in agent_names:
        # Format agent name nicely (capitalize and replace underscores)
        formatted_name = agent_name.replace("_", " ").title()

        lines.extend(
            [
                f"### {formatted_name}",
                "",
            ]
        )

        # Add agent output if available
        if agent_outputs and agent_name in agent_outputs:
            output = agent_outputs[agent_name]

            # Add issues
            if output.issues:
                lines.append("**Issues:**")
                lines.append("")
                for issue in output.issues:
                    lines.append(
                        f"- **[{issue.severity.upper()}]** {issue.location.file_path}:{issue.location.line_start} - {issue.description}"
                    )
                lines.append("")

            # Add notes
            if output.notes:
                lines.append("**Notes:**")
                lines.append("")
                for note in output.notes:
                    lines.append(f"- {note.note}")
                lines.append("")

    return "\n".join(lines)
