# AI Code Review Tool

## Overview

A minimalist CLI tool that performs automated code reviews using AI models. The
tool analyzes Git branch differences and generates review reports in Markdown
format. Supports three specialized review modes: comprehensive full reviews,
high-level summaries, and code quality/redundancy detection (spaghetti mode).
All reviews include an auto-generated executive summary for quick focus on
critical issues.

## Core Features

### CLI Interface

Simple command-line interface with sensible defaults:

- **Review Mode**: `full` (default), `summary`, or `spaghetti`
  - `full`: Comprehensive code review with detailed analysis
  - `summary`: High-level overview of changes
  - `spaghetti`: Code quality and redundancy detection (duplication, missed
    reuse opportunities, dead code, over-engineering)
- **Target Branch**: `main` (default) or user-specified (supports branch names
  and commit hashes)
- **Output File**: `review_{current_branch_name}.md` (default) or user-specified
- **Additional Instructions**: Optional markdown file with custom review
  guidelines
- **Executive Summary**: Auto-generated summary prepended to all reviews
  (disable with `--no-summary`)

The tool always reviews the currently checked out branch against the target
branch.

### Git Integration

- Works exclusively with Git repositories
- Analyzes differences between current branch (HEAD) and target branch
- Provides context-aware file analysis

### AI Model Integration

- **Multi-provider support:**
  - AWS Bedrock (default)
  - Anthropic API
  - Ollama (local models)
- Factory pattern architecture: Each provider in separate file, easy to extend
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

- Factory pattern for AI providers (function-based, matching tools pattern)
- Easy to add new model providers (one file + registry entry)
- Pluggable tool system

## Architecture

### Components

1. **CLI Parser**: Handle command-line arguments and defaults
2. **Git Interface**: Interact with Git to get diffs, file lists, and content
3. **AI Provider Layer**: Factory pattern with support for Bedrock, Anthropic,
   and Ollama
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

**All review modes include an executive summary at the top** that:

- Highlights the most critical issues (top 3-5)
- Shows issue counts by severity
- Provides actionable recommendations
- Uses emojis for visual clarity (🔴 CRITICAL, 🟠 HIGH, 🟡 MEDIUM, ⚪ LOW)

### Full Review Mode

Markdown file containing:

- Executive summary (auto-generated)
- Review summary
- File-by-file analysis
- Issues found (bugs, code smells, improvements)
- Security concerns
- Performance suggestions
- Best practice recommendations

### Summary Mode

Markdown file containing:

- Executive summary (auto-generated)
- High-level overview (2-4 sentences)
- Task-style description of changes
- Logical grouping of changes by purpose
- User impact (if applicable)
- New components and system integration
- Call graphs for complex interactions (if applicable)

### Spaghetti Code Detection Mode

Markdown file containing:

- Executive summary (auto-generated)
- Code quality assessment
- Code duplication analysis (within changes and across codebase)
- Redundancy detection (repeated patterns, checks, validations)
- Missed reuse opportunities (existing functions/classes that could be used)
- Library usage optimization (standard library or dependencies)
- Abstraction opportunities (inheritance, composition, interfaces)
- Dead/unreachable code detection
- Over-engineering concerns

## Technology Stack

- **Language**: Python 3.11+
- **AI Framework**: LangChain + LangGraph
- **AI Providers**:
  - AWS Bedrock (langchain-aws 1.1.0, boto3 1.42.15)
  - Anthropic API (langchain-anthropic 1.3.0)
  - Ollama (langchain-ollama 1.0.1)
- **VCS**: Git (via subprocess)
- **CLI**: argparse
- **Output**: Markdown (with mdformat for consistent formatting)

## Success Criteria

- Simple one-command usage
- Fast and token-efficient
- High-quality, actionable reviews
- Easy to extend with new AI providers
- Minimal setup and configuration
