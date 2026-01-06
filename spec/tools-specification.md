# Code Review Agent Tools

## Context

The agent receives all review context upfront in the initial message:

- **Commits**: List of commits between target branch and HEAD
- **Changed files**: List of files changed with additions/deletions counts
- **Diffs**: Full diff content for each file (truncated at 10k chars per file)

The agent has access to shared context for tool operations:

- `repo_path`: Absolute path to git repository
- `target_branch`: Base branch to compare against (e.g., "main")

______________________________________________________________________

## Tool 1: read_file_part

Read specific lines from a file (or entire file).

**Parameters:**

- `file_path`: Relative path from repo root
- `start_line`: First line to read, 1-indexed (optional)
- `end_line`: Last line to read, 1-indexed (optional)

**Returns:** FileContent object with:

- file_path, content (with line numbers), start_line, end_line, total_lines

______________________________________________________________________

## Tool 2: search_in_files

Search for text patterns across repository files.

**Parameters:**

- `pattern`: Text or regex pattern to search
- `file_pattern`: Glob pattern to limit files (optional)
- `context_lines`: Lines before/after match (default: 2)
- `max_results`: Maximum matches to return (default: 50)

**Returns:** List of SearchMatch objects with:

- file_path, line_number, line_content, match_context

______________________________________________________________________

## Tool 3: list_files

List files in repository or specific directory.

**Parameters:**

- `directory`: Directory to list (default: ".")
- `pattern`: Glob pattern to filter files (optional)

**Returns:** List of file paths (relative to repo root)

______________________________________________________________________

## Usage Strategy

1. Review the provided commits, changed files, and diffs in the initial message
2. For additional context beyond diffs:
   - Call `read_file_part` to see surrounding code
   - Call `search_in_files` to find related patterns
   - Call `list_files` to explore directory structure
3. Generate comprehensive review

## Error Handling

All tools return ToolMessage on errors:

- File not found
- Invalid ranges
- Git command failures
- Permission issues
