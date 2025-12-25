"""Helper utilities for tools."""


def truncate_line(line: str, max_length: int) -> str:
    """Truncate line if it exceeds max length."""
    if len(line) <= max_length:
        return line
    return line[:max_length] + " [truncated due to line size]"
