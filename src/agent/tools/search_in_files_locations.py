"""Search tracker that returns only match locations for expert agents."""

from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from pydantic import BaseModel

from ..prompts import get_prompt
from ..schema import Context
from .search_in_files import _search_in_files_impl


class FileMatches(BaseModel):
    """Matches in a single file."""

    file_path: str
    line_numbers: list[int]


class SearchResult(BaseModel):
    """Result containing only match locations, not content."""

    pattern: str
    total_matches: int
    files: list[FileMatches]


class SearchInFilesLocations:
    """Tracks search operations to prevent duplicates."""

    def __init__(self) -> None:
        """Initialize the tracker."""
        self.executed_searches: set[tuple[str, str | None]] = set()

    def _check_already_searched(self, pattern: str, file_pattern: str | None) -> bool:
        """Check if this exact search was already performed.

        Args:
            pattern: The search pattern
            file_pattern: Optional file pattern filter

        Returns:
            True if search was already performed
        """
        search_key = (pattern, file_pattern)
        return search_key in self.executed_searches

    def _record_search(self, pattern: str, file_pattern: str | None) -> None:
        """Record that search has been performed.

        Args:
            pattern: The search pattern
            file_pattern: Optional file pattern filter
        """
        search_key = (pattern, file_pattern)
        self.executed_searches.add(search_key)

    def create_tool(self) -> Any:
        """Create a tool function with this tracker instance bound to it.

        Returns:
            A tool function that can be used by LangChain agents
        """
        tracker = self

        @tool
        def search_in_files_locations(
            runtime: ToolRuntime[Context],
            pattern: str,
            reason: str,
            file_pattern: str | None = None,
        ) -> SearchResult | HumanMessage | ToolMessage:
            """Search for patterns and return only file locations, not content.

            ⚠️ CRITICAL: You can only search with the SAME parameters ONCE!
            - Check your conversation history before calling this tool
            - If you already searched for this pattern, use that information
            - Searching with identical pattern + file_pattern will be BLOCKED

            ⚠️ DO NOT USE THIS TOOL IF:
            - You already have the information in your context
            - You've already read a file - don't search in it again, reason about what you've seen
            - The matches are already provided in the findings or previous results
            - You can deduce the answer from information you already have

            💡 BATCH YOUR TOOL CALLS FOR EFFICIENCY:
            - Make multiple tool calls in parallel (ideally ~10 calls per agent loop)
            - Read all files you need at once instead of one-by-one
            - Example: If you need to check 5 files, call read_file_part 5 times in parallel
            - This is MUCH faster than sequential reads

            This tool returns WHERE matches were found (file path + line number),
            but not the actual content. You MUST use read_file_part to view the content.

            Args:
                pattern: The text or regex pattern to search for
                reason: Explanation of why you are searching
                file_pattern: Optional glob pattern (e.g., "*.py")

            Returns:
                SearchResult with locations grouped by file. Use read_file_part to get content.

            Example:
                1. search_in_files_locations("class Foo", "Finding Foo definition")
                   Returns: {files: [{file_path: "src/foo.py", line_numbers: [10, 25]}]}
                2. read_file_part("src/foo.py", "Reading Foo class", 10, 30)
                   Gets the actual content for all matches
            """
            if file_pattern:
                print(f"🔧 search_in_files: '{pattern}' in {file_pattern}")
            else:
                print(f"🔧 search_in_files: '{pattern}'")
            print(f"   Reason: {reason}")

            # Check if this exact search was already performed
            if tracker._check_already_searched(pattern, file_pattern):
                file_pattern_str = f" in {file_pattern}" if file_pattern else ""
                warning_template = get_prompt("duplicate_search_warning")
                warning_msg = warning_template.format(
                    pattern=pattern, file_pattern_str=file_pattern_str
                )

                print(f"   ⚠️  Search already performed!")

                return HumanMessage(
                    content=warning_msg,
                    tool_call_id=runtime.tool_call_id,
                )

            try:
                # Use the original search implementation
                matches = _search_in_files_impl(
                    repo_path=runtime.context.repo_path,
                    pattern=pattern,
                    file_pattern=file_pattern,
                    context_lines=0,  # We don't need context since we're not showing content
                    max_results=1000,
                    max_line_length=100,  # Doesn't matter since we're not showing content
                )

                # Group matches by file path
                files_dict: dict[str, list[int]] = {}
                for match in matches:
                    if match.file_path not in files_dict:
                        files_dict[match.file_path] = []
                    files_dict[match.file_path].append(match.line_number)

                # Convert to list of FileMatches
                files = [
                    FileMatches(file_path=path, line_numbers=line_numbers)
                    for path, line_numbers in files_dict.items()
                ]

                total = sum(len(f.line_numbers) for f in files)
                print(f"   ✓ Found {total} matches in {len(files)} files")

                # Record this search
                tracker._record_search(pattern, file_pattern)

                return SearchResult(
                    pattern=pattern,
                    total_matches=total,
                    files=files,
                )

            except Exception as e:
                print(f"   ✗ Error: {str(e)}")
                return ToolMessage(
                    content=f"Error searching for pattern {pattern}: {str(e)}",
                    tool_call_id=runtime.tool_call_id,
                )

        return search_in_files_locations
