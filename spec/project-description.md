# AI Code Review Tool

## Overview

A minimalist code review tool that performs automated code reviews using AI
models. Available as both a CLI tool and a GitHub Action. Analyzes Git branch
differences and generates comprehensive review reports with structured output
for consistent, machine-parseable results.

## Core Features

### Deployment Options

- **GitHub Action**: Automated PR reviews with inline comments and summary
- **CLI/Docker**: Local reviews with markdown output

### CLI Interface

Simple command-line interface with sensible defaults:

- **Target Branch**: `main` (default) or user-specified (supports branch names
  and commit hashes)
- **Output File**: `review_{current_branch_name}.md` (default) or user-specified
- **Additional Instructions**: Optional markdown file with custom review
  guidelines
- **Verification Mode**: Optional `--verify` flag enables
  [Chain-of-Verification](https://arxiv.org/abs/2309.11495) to reduce false
  positives
- **SAST Integration**: Optional `--sast` flag runs an
  [OpenGrep](https://github.com/opengrep/opengrep) pre-scan to augment the AI
  review with static analysis findings

The tool always reviews the currently checked out branch against the target
branch.

### GitHub Action

The action wraps the CLI and provides:

- Inline review comments on specific lines
- Summary comment with all issues
- Automatic resolution of previous review threads on re-runs
- Filtering by confidence level (when verification is enabled)

### Git Integration

- Works exclusively with Git repositories
- Analyzes differences between current branch (HEAD) and target branch
- Provides context-aware file analysis

### AI Model Integration

- **Multi-provider support:**
  - AWS Bedrock (default)
  - Anthropic API
  - Ollama (local models)
  - Moonshot
- Factory pattern architecture: Each provider in separate file, easy to extend
- Framework: LangChain for AI orchestration

## Context & Tools

The AI agent receives all review context upfront in the initial message:

- **Commits**: Full commit history between target branch and HEAD
- **Changed files**: List of files with change types and line counts
- **Diffs**: Complete diff content (truncated at 10k chars per file)

The agent also has access to these tools for additional analysis:

1. **read_file_part**: Read specific sections of files (with line numbers)
2. **list_files**: List files in the repository or specific directories
3. **search_in_files**: Search for specific patterns or text across files

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

**Python CLI:**

1. **CLI Parser**: Handle command-line arguments and defaults
2. **Git Interface**: Interact with Git to get diffs, file lists, and content
3. **AI Provider Layer**: Factory pattern with support for Bedrock, Anthropic,
   Ollama, and Moonshot
4. **LangChain Agent**: Orchestrate tools and AI to perform reviews
5. **Report Generator**: Format and write Markdown review reports

**GitHub Action (TypeScript):**

1. **Docker Runner**: Execute CLI via Docker with `--json` output
2. **GitHub API**: Post comments and reviews via Octokit
3. **Renderer**: Convert JSON output to markdown comments

### Workflow

1. User invokes CLI with optional parameters
2. Tool validates Git repository and determines current branch
3. Extract changed files between current branch (HEAD) and target
4. Initialize LangChain agent with tools
5. Agent analyzes changes using available tools
6. Generate comprehensive review in Markdown
7. Write to output file

## Output Format

**All reviews use structured output** rendered to markdown:

### Summary Section

High-level overview of changes including:

- Overview of the main purpose
- Key changes made
- Potentially risky areas

### Issues Summary Table

Quick overview of all issues with:

- Severity indicators (🔴 CRITICAL, 🟠 HIGH, 🟡 MEDIUM, 🟢 LOW)
- Title, category, and location

### Detailed Issues

Each issue includes:

- **Category**: LOGIC, SECURITY, ACCESS_CONTROL, PERFORMANCE, QUALITY,
  SIDE_EFFECTS, TESTING, DOCUMENTATION
- **Severity**: CRITICAL, HIGH, MEDIUM, LOW
- **Location**: File paths with optional line numbers
- **Explanation**: Detailed description of the problem
- **Suggested Fix**: Concrete recommendation with code snippets

## Technology Stack

- **Language**: Python 3.11+
- **AI Framework**: LangChain + LangGraph
- **AI Providers**:
  - AWS Bedrock (langchain-aws 1.1.0, boto3 1.42.15)
  - Anthropic API (langchain-anthropic 1.3.0)
  - Ollama (langchain-ollama 1.0.1)
  - Moonshot (langchain-openai - OpenAI-compatible API)
- **VCS**: Git (via subprocess)
- **CLI**: argparse
- **Output**: Markdown (with mdformat for consistent formatting)

## Success Criteria

- Simple one-command usage
- Fast and token-efficient
- High-quality, actionable reviews
- Easy to extend with new AI providers
- Minimal setup and configuration
