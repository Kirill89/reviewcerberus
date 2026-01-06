# Implementation Summary

## Overview

AI-powered code review tool that analyzes Git branch differences and generates
comprehensive review reports. Built with minimalism and token efficiency as core
principles.

**Key Features:**

- Three specialized review modes: full, summary, and spaghetti (code quality)
- Auto-generated executive summaries for all reviews
- Multi-provider support (AWS Bedrock, Anthropic API, and Ollama)
- Automatic context management for large PRs

**Tech Stack:**

- Python 3.11+
- LangChain 1.2.0 + LangGraph
- **Multi-provider support:**
  - AWS Bedrock Claude (boto3 1.42.15, langchain-aws 1.1.0)
  - Anthropic API (langchain-anthropic 1.3.0)
  - Ollama (langchain-ollama 1.0.1)
- Git (subprocess)
- pytest

**Code Quality:**

- mypy (strict type checking: `disallow_untyped_defs`, `warn_return_any`)
- black (code formatting)
- isort (import sorting)
- Makefile for test/lint/format commands

______________________________________________________________________

## Design Decisions

### 1. Multi-Provider Architecture

Support for AWS Bedrock, Anthropic API, and Ollama as alternative providers (not
simultaneous). User selects via `MODEL_PROVIDER` env variable.

**Factory Pattern Implementation:**

- Each provider in separate file under `src/agent/providers/`
- Function-based factories (matching tools pattern)
- Registry-based dispatch in `providers/__init__.py`
- Clean separation of provider-specific logic

**Key features:**

- Default to Bedrock for backward compatibility
- Prompt caching supported:
  - Bedrock: explicit cache points via `CachingBedrockClient`
  - Anthropic: automatic caching via SDK
  - Ollama: no caching (local inference)
- Clear error messages for missing credentials based on selected provider
- Easy to extend with new providers (add file + registry entry)

### 2. Simplified Branch Model

Always review HEAD vs target branch. No source_branch parameter - matches
natural git workflow (checkout branch → run review).

### 3. Context Provided Upfront

All review context is computed once and included in the initial user message:

- **Commits**: Full commit history between branches
- **Changed files**: List with additions/deletions counts
- **Diffs**: Complete diff for each file (truncated at 10k chars per file)

This eliminates tool call overhead for basic context gathering. The agent can
immediately start analyzing without needing to call tools for diffs or commits.

### 4. Tool Architecture Pattern

```python
# Business logic (pure, testable)
def _tool_impl(...) -> Result:
    return subprocess_result

# LangChain wrapper (error handling)
@tool
def tool_name(...) -> Result | ToolMessage:
    try:
        return _tool_impl(...)
    except Exception as e:
        return ToolMessage(...)
```

### 6. Progress Visualization

Real-time progress display:

- Thinking duration (🤔 with timing)
- Tool calls logged directly from @tool wrappers (🔧)
- Simple, clean output
- Token usage summary at end

### 7. Configuration via Environment Variables

All configuration centralized in `src/config.py`:

- Provider selection (MODEL_PROVIDER)
- AWS credentials (for Bedrock)
- Anthropic API key (for Anthropic API)
- Model name and parameters
- Recursion limit
- Overridable via .env file

### 8. Additional Instructions

Users can provide custom review guidelines via `--instructions` parameter,
allowing project-specific review criteria.

### 9. Context Management & Summarization

Automatic context management prevents token limit exhaustion during large PR
reviews:

**Architecture:**

- `SummarizingMiddleware` monitors token count in agent loop
- Triggers at `CONTEXT_COMPACT_THRESHOLD` (provider-specific defaults)
- Injects summarization request into conversation
- Agent generates summary of findings so far
- Middleware compacts history: keeps only [initial request + summary]
- Agent continues review with freed tokens

**Key Features:**

- Custom summary prompt (`REVIEW_SUMMARY_PROMPT`) preserves:
  - Files analyzed and findings discovered (by severity)
  - Files remaining to review
  - Investigation threads and next steps
- Default: 140k tokens for all providers
- Configurable threshold via `CONTEXT_COMPACT_THRESHOLD` env var
- Transparent logging when summarization triggers

### 10. Tool Output Protection

Tools implement line truncation to prevent context explosion from minified
code/generated files:

**search_in_files:**

- Lines truncated to 300 characters
- Appends `[truncated due to line size]` message
- Prevents massive outputs (e.g., 669k char lines in JSON files)
- Test coverage: `test_search_in_files_truncates_long_lines`

**Impact:**

- Without truncation: 438k tokens from 25 matches (context explosion)
- With truncation: 1.5k tokens from 25 matches (295x reduction)

### 11. Review Modes

Three specialized review modes available:

**Full Mode (default):**

- Comprehensive code review with detailed analysis
- Checks logic, security, performance, code quality, side effects, testing
- Produces prioritized issue list with severity levels

**Summary Mode:**

- High-level overview of changes
- Task-style description and logical grouping
- User impact analysis and system integration overview

**Spaghetti Mode:**

- Code quality and redundancy detection
- Actively searches codebase for similar patterns using `search_in_files`
- Detects: duplication, missed reuse opportunities, redundant patterns, dead
  code, over-engineering
- Suggests: library usage, abstraction opportunities, refactoring

### 12. Executive Summary

All reviews automatically include an AI-generated executive summary prepended to
the top:

**Architecture:**

- Post-processing step after main review generation
- Simple LLM call (fast, no agent overhead)
- Uses conversational prompt validated through user testing
- Formatted with `_format_review_content()` for uniform markdown

**Summary Contains:**

- Issue counts by severity (with emojis: 🔴 CRITICAL, 🟠 HIGH, etc.)
- Top 3-5 most critical issues with locations
- Brief recommendation on priorities
- Concise (1 page max, ~300-500 words)

**Configuration:**

- Enabled by default for all modes
- Disable with `--no-summary` flag for faster reviews
- Token usage tracked and merged with main review

______________________________________________________________________

## Project Structure

```
reviewcerberus/
├── src/
│   ├── config.py                        # Configuration (env vars)
│   ├── main.py                          # CLI entry point
│   └── agent/
│       ├── agent.py                     # Agent setup
│       ├── model.py                     # Model setup (factory)
│       ├── providers/                   # Model providers (factory pattern)
│       │   ├── __init__.py              # Factory + registry
│       │   ├── bedrock.py               # Bedrock provider
│       │   ├── bedrock_caching.py       # Bedrock caching wrapper
│       │   ├── anthropic.py             # Anthropic provider
│       │   └── ollama.py                # Ollama provider
│       ├── prompts/                     # Review prompts
│       │   ├── __init__.py              # Prompt loader
│       │   ├── full_review.md           # Full review mode prompt
│       │   ├── summary_mode.md          # Summary mode prompt
│       │   ├── spaghetti_code_detection.md  # Spaghetti mode prompt
│       │   ├── executive_summary.md     # Executive summary prompt
│       │   └── context_summary.md       # Context compaction prompt
│       ├── git_utils/                   # Git operations
│       │   ├── get_changed_files.py     # List changed files
│       │   ├── get_commit_messages.py   # Get commit history
│       │   ├── get_file_diff.py         # Get file diffs
│       │   └── types.py                 # FileChange, CommitInfo models
│       ├── formatting/                  # Context and output formatting
│       │   ├── build_review_context.py  # Build initial context message
│       │   └── format_review_content.py # Format markdown output
│       ├── schema.py                    # Context model
│       ├── runner.py                    # Agent runner + summarize_review()
│       ├── progress_callback_handler.py # Progress display
│       └── tools/                       # 3 review tools
│
├── tests/                         # Integration tests
│   └── agent/
│       ├── git_utils/             # Tests for git utilities
│       └── tools/                 # Tests for tools
│
└── spec/                          # Documentation
    ├── project-description.md
    ├── tools-specification.md
    └── implementation-summary.md  (this file)
```

______________________________________________________________________

## Implemented Tools

1. **read_file_part** - Read file content with line ranges
2. **search_in_files** - Search patterns across codebase
3. **list_files** - List repository files

**Note**: Changed files, commit messages, and diffs are provided upfront in the
initial context message, not via tools.

______________________________________________________________________

## Testing Strategy

Integration tests with real git repositories:

- No mocking of git commands
- Context manager creates/cleans temp repos
- Tests call \_impl functions directly
- One scenario per test

______________________________________________________________________

## Code Quality & Tooling

### Makefile Commands

```bash
make test    # Run pytest
make lint    # Run mypy, isort --check, black --check
make format  # Run isort and black to auto-format
```

### Type Checking (mypy)

```toml
[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
warn_return_any = true           # Warn about implicit Any returns
warn_unused_configs = true       # Warn about unused config
disallow_untyped_defs = true     # All functions need type annotations
```

All functions must have complete type signatures:

```python
def my_function(x: int, y: str) -> bool:  # ✓ Good
    return True

def my_function(x, y):  # ✗ Error: missing annotations
    return True
```

### Code Formatting

- **black**: Automatic code formatting (line length 88)
- **isort**: Import sorting with black profile for compatibility

______________________________________________________________________

## Token Efficiency

- All context (commits, files, diffs) provided upfront in initial message
- Diff truncation at 10k characters per file (configurable via
  MAX_DIFF_PER_FILE)
- Line range reading for additional file context
- Limited search results (default 50)
- Prompt caching enabled

______________________________________________________________________

## Guidelines

### Adding New Providers

1. Create `src/agent/providers/provider_name.py`
2. Implement `create_provider_model(model_name: str, max_tokens: int) -> Any`
3. Add to `PROVIDER_REGISTRY` in `providers/__init__.py`
4. Update `src/config.py`:
   - Add provider-specific env vars
   - Add default MODEL_NAME for provider
   - Add validation logic
5. Update `.env.example` with configuration example
6. Update documentation (README.md, DOCKERHUB.md, spec files)

### Adding New Tools

1. Implement `_tool_name_impl` (business logic - pure, no logging)
2. Add `@tool` wrapper (logging + error handling)
3. Create test in tests/agent/tools/
4. Export from tools/__init__.py
5. Register in agent.py tools list
6. Update spec/tools-specification.md

### Code Style

- Minimalism first
- No unnecessary abstractions
- Code should be self-documenting
- **Strict type checking**: All functions must have complete type annotations
  (enforced by mypy)
- Return types required for all functions (including `-> None`)
- Use `Any` type for complex third-party types without proper stubs
- Keep functions small

### Testing

- Integration over unit tests
- Use real git operations
- Test \_impl functions directly
- Minimal but thorough assertions
- Run with `make test` or `poetry run pytest -v`

### Progress Display

- Each `@tool` wrapper logs directly with `print()`
- Simple format: `🔧 tool_name: key_info`
- Error logging: `✗ Error: message`
- Callback handler tracks thinking duration
- No complex parsing needed

______________________________________________________________________

## Configuration

**.env (Bedrock):**

```bash
MODEL_PROVIDER=bedrock  # default
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION_NAME=us-east-1
MODEL_NAME=us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

**.env (Anthropic API):**

```bash
MODEL_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
MODEL_NAME=claude-sonnet-4-5-20250929
```

**.env (Ollama):**

```bash
MODEL_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434      # optional, default
MODEL_NAME=devstral-small-2:24b-cloud       # optional, default
```

**Model Initialization:**

- Factory pattern: `src/agent/model.py` uses `create_model()` from providers
- Registry-based: Each provider registered in `PROVIDER_REGISTRY` dict
- Provider files: `providers/bedrock.py`, `providers/anthropic.py`,
  `providers/ollama.py`
- Each provider exports `create_<provider>_model(model_name, max_tokens)`
  function

______________________________________________________________________

## Usage

```bash
# Basic usage (full review with executive summary)
poetry run reviewcerberus

# Different review modes
poetry run reviewcerberus --mode full       # Comprehensive review
poetry run reviewcerberus --mode summary    # High-level overview
poetry run reviewcerberus --mode spaghetti  # Code quality/redundancy

# Specify target branch
poetry run reviewcerberus --target-branch develop

# Custom output file
poetry run reviewcerberus --output my-review.md

# Specify repository path
poetry run reviewcerberus --repo-path /path/to/repo

# Additional review instructions
poetry run reviewcerberus --instructions guidelines.md

# Skip executive summary (faster)
poetry run reviewcerberus --no-summary
```

______________________________________________________________________

## Common Pitfalls

### ❌ Don't

- Add source_branch parameter back
- Mock git in tests
- Put error handling or logging in \_impl functions
- Add verbose parameters to \_impl functions

### ✅ Do

- Keep business logic in \_impl (pure functions)
- Log from @tool wrappers (using print)
- Use real git operations
- Let \_impl raise exceptions
- Keep it simple
- Run `make lint` before committing
- Add type annotations to all new functions
