"""Format review content output."""

import mdformat


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
