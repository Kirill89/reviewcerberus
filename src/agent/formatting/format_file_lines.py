"""Utility for formatting file lines with line numbers."""

# Canonical structure for file content: {file_path: {line_number: line_content}}
FileLinesMap = dict[str, dict[int, str]]

# Default max line length to prevent context explosion from minified code
DEFAULT_MAX_LINE_LENGTH = 500


def format_file_lines(
    files: FileLinesMap,
    max_line_length: int = DEFAULT_MAX_LINE_LENGTH,
    file_totals: dict[str, int] | None = None,
) -> str:
    """Format file lines with line numbers as markdown.

    Args:
        files: Dictionary mapping file paths to their lines.
               Structure: {file_path: {line_number: line_content}}
        max_line_length: Max length per line. Lines exceeding this will be
                        truncated. Defaults to 500.
        file_totals: Optional dict mapping file paths to their total line counts.
                    When provided, shows total in the header.

    Returns:
        Markdown string with each file as a section containing numbered lines.
    """
    if not files:
        return ""

    parts: list[str] = []

    for file_path in sorted(files.keys()):
        lines = files[file_path]
        if not lines:
            continue

        sorted_line_nums = sorted(lines.keys())
        content_lines: list[str] = []

        for line_num in sorted_line_nums:
            content = lines[line_num]
            if max_line_length and len(content) > max_line_length:
                content = content[:max_line_length] + " [truncated due to line size]"
            content_lines.append(f"{line_num:6d}\t{content}")

        content = "\n".join(content_lines)

        # Build header with optional total lines
        if file_totals and file_path in file_totals:
            header = f"## {file_path} ({file_totals[file_path]} lines total)"
        else:
            header = f"## {file_path}"

        parts.append(f"{header}\n\n```\n{content}\n```")

    return "\n\n".join(parts)
