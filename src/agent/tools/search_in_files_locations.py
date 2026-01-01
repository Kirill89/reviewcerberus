"""Search tracker that returns only match locations for expert agents."""

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from pydantic import BaseModel

from ..schema import Context
from .search_in_files import _search_in_files_impl


class SearchLocation(BaseModel):
    """Location of a search match without content."""

    file_path: str
    line_number: int


class SearchResult(BaseModel):
    """Result containing only match locations, not content."""

    pattern: str
    total_matches: int
    locations: list[SearchLocation]


@tool
def search_in_files_locations(
    runtime: ToolRuntime[Context],
    pattern: str,
    reason: str,
    file_pattern: str | None = None,
    max_results: int = 50,
) -> SearchResult | ToolMessage:
    """Search for patterns and return only file locations, not content.

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
        max_results: Maximum number of results. Defaults to 50.

    Returns:
        SearchResult with locations only. Use read_file_part to get content.

    Example:
        1. search_in_files_locations("class Foo", "Finding Foo definition")
           Returns: Found in src/foo.py line 10
        2. read_file_part("src/foo.py", "Reading Foo class", 10, 20)
           Gets the actual content
    """
    if file_pattern:
        print(f"🔧 search_in_files: '{pattern}' in {file_pattern}")
    else:
        print(f"🔧 search_in_files: '{pattern}'")
    print(f"   Reason: {reason}")

    try:
        # Use the original search implementation
        matches = _search_in_files_impl(
            repo_path=runtime.context.repo_path,
            pattern=pattern,
            file_pattern=file_pattern,
            context_lines=0,  # We don't need context since we're not showing content
            max_results=max_results,
            max_line_length=100,  # Doesn't matter since we're not showing content
        )

        # Extract only locations, not content
        locations = [
            SearchLocation(file_path=match.file_path, line_number=match.line_number)
            for match in matches
        ]

        print(f"   ✓ Found {len(locations)} matches")

        return SearchResult(
            pattern=pattern,
            total_matches=len(locations),
            locations=locations,
        )

    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        return ToolMessage(
            content=f"Error searching for pattern {pattern}: {str(e)}",
            tool_call_id=runtime.tool_call_id,
        )
