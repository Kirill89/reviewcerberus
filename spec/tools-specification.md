# Code Review Agent Tools

## Context

The agent has access to shared context:

- `repo_path`: Absolute path to git repository
- `target_branch`: Base branch to compare against (e.g., "main")
- `changed_files`: List of files changed between target and HEAD

All tools operate on HEAD (current branch) vs target branch.

______________________________________________________________________

## Tool 1: changed_files

List all files changed between target branch and HEAD.

**Parameters:** None (uses context)

**Returns:** List of FileChange objects with:

- path, change_type, old_path, additions, deletions

______________________________________________________________________

## Tool 2: get_commit_messages

Get commit messages between target branch and HEAD.

**Parameters:**

- `max_commits`: Maximum commits to retrieve (default: 20)

**Returns:** List of CommitInfo objects with:

- sha, author, date, message

______________________________________________________________________

## Tool 3: diff_file

Show git diff for a specific file with hunk pagination.

**Parameters:**

- `file_path`: Relative path from repo root
- `context_lines`: Unchanged lines around changes (default: 3)
- `start_hunk`: First hunk to return, 1-indexed (default: 1)
- `end_hunk`: Last hunk to return, inclusive (default: 20)

**Returns:** FileDiff object with:

- file_path, diff, additions, deletions
- total_hunks, returned_hunks, start_hunk, end_hunk

**Notes:**

- Hunks are semantic units (each @@ section)
- Agent can paginate: 1-20, then 21-40, etc.
- Won't truncate mid-change

______________________________________________________________________

## Tool 4: read_file_part

Read specific lines from a file (or entire file).

**Parameters:**

- `file_path`: Relative path from repo root
- `start_line`: First line to read, 1-indexed (optional)
- `end_line`: Last line to read, 1-indexed (optional)

**Returns:** FileContent object with:

- file_path, content (with line numbers), start_line, end_line, total_lines

______________________________________________________________________

## Tool 5: search_in_files

Search for text patterns across repository files.

**Parameters:**

- `pattern`: Text or regex pattern to search
- `file_pattern`: Glob pattern to limit files (optional)
- `context_lines`: Lines before/after match (default: 2)
- `max_results`: Maximum matches to return (default: 50)

**Returns:** List of SearchMatch objects with:

- file_path, line_number, line_content, match_context

______________________________________________________________________

## Tool 6: list_files

List files in repository or specific directory.

**Parameters:**

- `directory`: Directory to list (default: ".")
- `pattern`: Glob pattern to filter files (optional)

**Returns:** List of file paths (relative to repo root)

______________________________________________________________________

## Usage Strategy

1. Review `changed_files` in context for overview
2. Call `get_commit_messages` to understand intent
3. For each important file:
   - Call `diff_file` to see changes
   - Call `read_file_part` for additional context
   - Call `search_in_files` to find related code
4. Generate comprehensive review

## Error Handling

All tools return ToolMessage on errors:

- File not found
- Invalid ranges
- Git command failures
- Permission issues
