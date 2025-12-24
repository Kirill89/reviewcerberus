# Implementation Summary

## Overview

AI-powered code review tool that analyzes Git branch differences and generates
comprehensive review reports. Built with minimalism and token efficiency as core
principles.

**Tech Stack:**

- Python 3.11+
- LangChain 1.2.0 + LangGraph
- **Multi-provider support:**
  - AWS Bedrock Claude (boto3 1.42.15, langchain-aws 1.1.0)
  - Anthropic API (langchain-anthropic 1.3.0)
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

Support both AWS Bedrock and Anthropic API as alternative providers (not
simultaneous). User selects via `MODEL_PROVIDER` env variable. Provider-specific
initialization is conditional to avoid unnecessary dependencies.

**Key features:**

- Default to Bedrock for backward compatibility
- Prompt caching supported for both providers (Bedrock: explicit cache points,
  Anthropic: automatic caching)
- Clear error messages for missing credentials based on selected provider
- All imports at top level (no conditional imports)

### 2. Simplified Branch Model

Always review HEAD vs target branch. No source_branch parameter - matches
natural git workflow (checkout branch → run review).

### 3. Changed Files in Context

Computed once at initialization and provided directly to agent. Saves tool call
overhead.

### 4. Hunk-Based Diff Pagination

Use semantic units (@@...@@ sections) instead of line numbers. Default 1-20
hunks. Agent can paginate.

### 5. Tool Architecture Pattern

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

______________________________________________________________________

## Project Structure

```
reviewcerberus/
├── src/
│   ├── config.py                        # Configuration (env vars)
│   ├── main.py                          # CLI entry point
│   └── agent/
│       ├── agent.py                     # Agent setup
│       ├── model.py                     # Model setup (multi-provider)
│       ├── caching_bedrock_client.py    # Bedrock caching wrapper
│       ├── system.py                    # Review prompt
│       ├── schema.py                    # Context model
│       ├── runner.py                    # Agent runner
│       ├── progress_callback_handler.py # Progress display
│       └── tools/                       # 6 review tools
│
├── tests/                         # Integration tests
│   └── agent/tools/               # Test per tool
│
└── spec/                          # Documentation
    ├── project-description.md
    ├── tools-specification.md
    └── implementation-summary.md  (this file)
```

______________________________________________________________________

## Implemented Tools

1. **changed_files** - List changed files
2. **get_commit_messages** - Get commit history
3. **diff_file** - Show git diff with pagination
4. **read_file_part** - Read file content
5. **search_in_files** - Search patterns
6. **list_files** - List repository files

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

- Changed files in context (not via tool)
- Hunk-based pagination (default 20)
- Line range reading
- Limited search results (default 50)
- Configurable context lines
- Prompt caching enabled

______________________________________________________________________

## Guidelines

### Adding New Tools

1. Implement `_tool_name_impl` (business logic - pure, no logging)
2. Add `@tool` wrapper (logging + error handling)
3. Create test
4. Export from tools/__init__.py
5. Update tools-specification.md

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

**Model Initialization (src/agent/model.py):**

```python
# All imports at top level (no conditional imports)
from typing import Any
import boto3
from botocore.config import Config
from langchain.chat_models import init_chat_model
from langchain_anthropic import ChatAnthropic

# Provider-specific initialization
if MODEL_PROVIDER == "bedrock":
    bedrock_client = boto3.client(...)
    caching_client = CachingBedrockClient(bedrock_client)
    model = init_chat_model(
        MODEL_NAME,
        client=caching_client,
        model_provider="bedrock_converse",
        temperature=0.0,
        max_tokens=MAX_OUTPUT_TOKENS,
    )
elif MODEL_PROVIDER == "anthropic":
    # ChatAnthropic automatically uses ANTHROPIC_API_KEY environment variable
    base_model = ChatAnthropic(
        model_name=MODEL_NAME,
        temperature=0.0,
        max_tokens_to_sample=MAX_OUTPUT_TOKENS,
    )
    model = CachingAnthropicClient(base_model)
```

______________________________________________________________________

## Usage

```bash
# Basic usage
poetry run reviewcerberus

# Specify target branch
poetry run reviewcerberus --target-branch develop

# Custom output file
poetry run reviewcerberus --output my-review.md

# Specify repository path
poetry run reviewcerberus --repo-path /path/to/repo

# Additional review instructions
poetry run reviewcerberus --instructions guidelines.md
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
