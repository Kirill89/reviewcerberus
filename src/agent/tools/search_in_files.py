import subprocess

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from pydantic import BaseModel

from ..schema import Context


class SearchMatch(BaseModel):
    file_path: str
    line_number: int
    line_content: str
    match_context: str


def _truncate_line(line: str, max_length: int) -> str:
    """Truncate line if it exceeds max length."""
    if len(line) <= max_length:
        return line
    return line[:max_length] + " [truncated due to line size]"


def _search_in_files_impl(
    repo_path: str,
    pattern: str,
    file_pattern: str | None = None,
    context_lines: int = 2,
    max_results: int = 50,
    max_line_length: int = 300,
) -> list[SearchMatch]:
    cmd = ["git", "-C", repo_path, "grep", "-n", f"-C{context_lines}", pattern, "HEAD"]
    if file_pattern:
        cmd.extend(["--", file_pattern])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 and result.returncode != 1:
        raise RuntimeError(f"Git grep failed: {result.stderr}")

    matches = []
    lines = result.stdout.splitlines()

    current_file = None
    current_line_num = None
    current_content = []

    for line in lines[: max_results * 5]:
        if line.startswith("--"):
            continue

        if line.startswith("HEAD:") and ":" in line[5:]:
            rest = line[5:]
            parts = rest.split(":", 2)
            if len(parts) >= 3:
                file_path = parts[0]
                line_num_str = parts[1]
                content = parts[2]

                if line_num_str.isdigit():
                    if current_file and current_line_num:
                        matches.append(
                            SearchMatch(
                                file_path=current_file,
                                line_number=current_line_num,
                                line_content=(
                                    _truncate_line(current_content[0], max_line_length)
                                    if current_content
                                    else ""
                                ),
                                match_context="\n".join(
                                    _truncate_line(line, max_line_length)
                                    for line in current_content
                                ),
                            )
                        )
                        if len(matches) >= max_results:
                            break

                    current_file = file_path
                    current_line_num = int(line_num_str)
                    current_content = [content]
                else:
                    if current_content:
                        current_content.append(content)

    if current_file and current_line_num and len(matches) < max_results:
        matches.append(
            SearchMatch(
                file_path=current_file,
                line_number=current_line_num,
                line_content=(
                    _truncate_line(current_content[0], max_line_length)
                    if current_content
                    else ""
                ),
                match_context="\n".join(
                    _truncate_line(line, max_line_length) for line in current_content
                ),
            )
        )

    return matches


@tool
def search_in_files(
    runtime: ToolRuntime[Context],
    pattern: str,
    file_pattern: str | None = None,
    context_lines: int = 2,
    max_results: int = 50,
    max_line_length: int = 300,
) -> list[SearchMatch] | ToolMessage:
    """Search for text patterns across files in the repository.

    Lines longer than max_line_length characters will be truncated to prevent
    massive outputs from minified code or generated files.
    """
    if file_pattern:
        print(f"🔧 search_in_files: '{pattern}' in {file_pattern}")
    else:
        print(f"🔧 search_in_files: '{pattern}'")
    try:
        return _search_in_files_impl(
            runtime.context.repo_path,
            pattern,
            file_pattern,
            context_lines,
            max_results,
            max_line_length,
        )
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        return ToolMessage(
            content=f"Error searching for pattern {pattern}: {str(e)}",
            tool_call_id=runtime.tool_call_id,
        )
