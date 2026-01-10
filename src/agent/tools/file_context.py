"""FileContext class for tracking file content across tool calls."""

from __future__ import annotations

from ..formatting.format_file_lines import FileLinesMap, format_file_lines


class FileContext:
    """Tracks file content read by agent tools for context transfer.

    This class maintains a record of all file lines that have been read
    during tool execution, allowing context to be transferred between
    different agents.

    Attributes:
        files: Dictionary mapping file paths to their tracked lines.
               Structure: {file_path: {line_number: line_content}}
    """

    def __init__(self) -> None:
        self.files: FileLinesMap = {}

    def update(self, lines: FileLinesMap) -> None:
        """Merge lines from multiple files into tracked state.

        Args:
            lines: FileLinesMap to merge into current state
        """
        for file_path, file_lines in lines.items():
            if file_path not in self.files:
                self.files[file_path] = {}
            self.files[file_path].update(file_lines)

    def to_markdown(self) -> str:
        """Render all tracked file content as markdown.

        Returns:
            Markdown string with all tracked files, each with a header
            and code block containing the tracked lines.
        """
        return format_file_lines(self.files)

    def clear(self) -> None:
        """Clear all tracked file content."""
        self.files.clear()
