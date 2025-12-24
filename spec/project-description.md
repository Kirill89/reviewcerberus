# AI Code Review Tool

## Overview

A minimalist CLI tool that performs automated code reviews using AI models. The
tool analyzes Git branch differences and generates comprehensive review reports
in Markdown format.

## Core Features

### CLI Interface

Simple command-line interface with sensible defaults:

- **Target Branch**: `main` (default) or user-specified
- **Output File**: `review_{current_branch_name}.md` (default) or user-specified

The tool always reviews the currently checked out branch against the target
branch.

### Git Integration

- Works exclusively with Git repositories
- Analyzes differences between current branch (HEAD) and target branch
- Provides context-aware file analysis

### AI Model Integration

- Primary support: AWS Bedrock models
- Architecture: Designed for easy extensibility to support other AI providers
  with minimal code changes
- Framework: LangChain for AI orchestration

## LangChain Tools

The AI agent will have access to the following tools to perform code reviews:

1. **read_file_part**: Read specific sections of files (with line numbers) to
   reduce token usage
2. **diff_file**: Show Git diff for a specific file (supports partial diffs to
   reduce tokens)
3. **list_files**: List files in the repository or specific directories
4. **search_in_files**: Search for specific patterns or text across files
5. **get_commit_messages**: Get commit messages to understand change intent

**Note**: The list of changed files is provided directly in the agent's context
at initialization, eliminating the need for a separate tool call.

## Design Principles

### Minimalism

- Keep dependencies minimal
- Simple, focused functionality
- Clean, readable codebase
- No unnecessary features

### Token Efficiency

- All tools support partial/chunked operations
- Avoid loading entire files when possible
- Smart diff viewing (context-aware snippets)

### Extensibility

- Abstract AI provider interface
- Easy to add new model providers
- Pluggable tool system

## Architecture

### Components

1. **CLI Parser**: Handle command-line arguments and defaults
2. **Git Interface**: Interact with Git to get diffs, file lists, and content
3. **AI Provider Layer**: Abstract interface for AI models (Bedrock initially)
4. **LangChain Agent**: Orchestrate tools and AI to perform reviews
5. **Report Generator**: Format and write Markdown review reports

### Workflow

1. User invokes CLI with optional parameters
2. Tool validates Git repository and determines current branch
3. Extract changed files between current branch (HEAD) and target
4. Initialize LangChain agent with tools
5. Agent analyzes changes using available tools
6. Generate comprehensive review in Markdown
7. Write to output file

## Output Format

Markdown file containing:

- Review summary
- File-by-file analysis
- Issues found (bugs, code smells, improvements)
- Security concerns
- Performance suggestions
- Best practice recommendations

## Technology Stack

- **Language**: Python
- **AI Framework**: LangChain
- **AI Provider**: AWS Bedrock (with extensible provider pattern)
- **VCS**: Git (via subprocess or GitPython)
- **CLI**: argparse or click
- **Output**: Markdown

## Success Criteria

- Simple one-command usage
- Fast and token-efficient
- High-quality, actionable reviews
- Easy to extend with new AI providers
- Minimal setup and configuration
