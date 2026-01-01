"""Read file tool to prevent duplicate file reads in expert agents."""

import subprocess
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from pydantic import BaseModel

from ..prompts import get_prompt
from ..schema import Context
from .helpers import truncate_line


class FileContent(BaseModel):
    """Full file content with truncation info."""

    file_path: str
    content: str
    total_lines: int
    was_truncated: bool


class ReadFile:
    """Tracks accessed files and prevents duplicate reads.

    This wrapper reads entire files at once with smart truncation:
    - Lines longer than max_line_length are truncated
    - Files longer than max_lines are truncated with a message
    - Each file can only be read once
    """

    def __init__(self, max_lines: int = 1000, max_line_length: int = 500):
        """Initialize the tracker.

        Args:
            max_lines: Maximum number of lines to read before truncating file
            max_line_length: Maximum length for each line before truncating
        """
        self.accessed_files: set[str] = set()
        self.max_lines = max_lines
        self.max_line_length = max_line_length

    def _check_already_read(self, file_path: str) -> bool:
        """Check if file was already read.

        Args:
            file_path: The file path being requested

        Returns:
            True if file was already read
        """
        return file_path in self.accessed_files

    def _record_access(self, file_path: str) -> None:
        """Record that file has been accessed.

        Args:
            file_path: The file path being accessed
        """
        self.accessed_files.add(file_path)

    def _read_full_file(self, repo_path: str, file_path: str) -> FileContent:
        """Read entire file with smart truncation.

        Args:
            repo_path: Repository root path
            file_path: Path to file relative to repo root

        Returns:
            FileContent with entire file (or truncated if too long)
        """
        result = subprocess.run(
            ["git", "-C", repo_path, "show", f"HEAD:{file_path}"],
            capture_output=True,
            text=True,
            check=True,
        )

        lines = result.stdout.splitlines()
        total_lines = len(lines)

        # Determine if we need to truncate
        was_truncated = total_lines > self.max_lines
        lines_to_show = lines[: self.max_lines] if was_truncated else lines

        # Format lines with line numbers and truncation
        formatted_lines = [
            f"{i + 1:6d}\t{truncate_line(line, self.max_line_length)}"
            for i, line in enumerate(lines_to_show)
        ]

        content = "\n".join(formatted_lines)

        # Add truncation message if needed
        if was_truncated:
            content += (
                f"\n\n[... File truncated after {self.max_lines} lines. "
                f"Total file has {total_lines} lines. "
                f"Remaining {total_lines - self.max_lines} lines not shown to save tokens ...]"
            )

        return FileContent(
            file_path=file_path,
            content=content,
            total_lines=total_lines,
            was_truncated=was_truncated,
        )

    def create_tool(self) -> Any:
        """Create a tool function with this tracker instance bound to it.

        Returns:
            A tool function that can be used by LangChain agents
        """
        tracker = self

        @tool
        def read_file(
            runtime: ToolRuntime[Context],
            file_path: str,
            reason: str,
        ) -> FileContent | HumanMessage | ToolMessage:
            """Read an entire file at once.

            ⚠️ CRITICAL: You can only read each file ONCE!
            - Check your conversation history before calling this tool
            - If you already read this file, use that information
            - Reading the same file twice will be BLOCKED

            💡 BATCH YOUR TOOL CALLS FOR EFFICIENCY:
            - Make multiple tool calls in parallel (ideally ~10 calls per agent loop)
            - Read all files you need at once instead of one-by-one
            - Example: If you need to check 5 files, call read_file 5 times in parallel
            - This is MUCH faster than sequential reads

            The tool automatically handles large files:
            - Lines longer than 500 chars are truncated with a message
            - Files longer than 1000 lines are truncated with a message
            - You'll see the first 1000 lines, which is usually sufficient

            Args:
                file_path: Path to the file relative to repository root
                reason: Explanation of why you are reading this file (e.g., "Checking error handling implementation")

            Returns:
                Full file content with line numbers (or truncated if very large)

            Examples:
                - read_file("src/main.py", "Checking error handling")
                - read_file("src/utils.py", "Looking for helper functions")
            """
            print(f"🔧 read_file: {file_path}")
            print(f"   Reason: {reason}")

            # Check if file was already read
            if tracker._check_already_read(file_path):
                warning_template = get_prompt("duplicate_read_warning")
                warning_msg = warning_template.format(
                    lines_str="entire file", file_path=file_path
                )

                print(f"   ⚠️  File already read!")

                return HumanMessage(
                    content=warning_msg,
                    tool_call_id=runtime.tool_call_id,
                )

            try:
                # Read the entire file
                content_result = tracker._read_full_file(
                    runtime.context.repo_path,
                    file_path,
                )

                # Record access
                tracker._record_access(file_path)

                if content_result.was_truncated:
                    print(
                        f"   ⚠️  File truncated! Showing first {tracker.max_lines} of {content_result.total_lines} lines"
                    )
                    print(
                        f"   ✓ Read {content_result.total_lines} lines (truncated to {tracker.max_lines})"
                    )
                else:
                    print(f"   ✓ Read {content_result.total_lines} lines")

                return content_result

            except Exception as e:
                print(f"   ✗ Error: {str(e)}")
                return ToolMessage(
                    content=f"Error reading file {file_path}: {str(e)}",
                    tool_call_id=runtime.tool_call_id,
                )

        return read_file
