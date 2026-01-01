# Implementation Summary

## Overview

AI-powered code review tool that analyzes Git branch differences and generates
comprehensive review reports. Built with minimalism and token efficiency as core
principles.

**Key Features:**

- Five specialized review modes: full, summary, spaghetti (code quality),
  security (OWASP Top 10), and expert (two-stage with validation)
- Auto-generated executive summaries for most reviews
- Multi-provider support (AWS Bedrock, Anthropic API, and Ollama)
- Automatic context management for large PRs
- Expert mode: two-stage review process that filters false positives

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

Five specialized review modes available:

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

**Security Mode:**

- OWASP Top 10 security analysis
- Data flow tracing from user input to dangerous sinks
- Exploitability assessment for each finding
- Comprehensive security posture overview

**Expert Mode:**

- Two-stage review process (primary + validation)
- Stage 1: Comprehensive analysis identifies potential findings
- Stage 2: Validation agent confirms or rejects each finding
- Only confirmed findings appear in final report
- Token usage monitoring with context window warnings
- Smart tool tracking (duplicate reads, consecutive reads)
- Structured output with Pydantic schemas
- Best for high-stakes reviews requiring high accuracy

### 12. Executive Summary

Most reviews automatically include an AI-generated executive summary prepended
to the top:

**Architecture:**

- Post-processing step after main review generation
- Simple LLM call (fast, no agent overhead)
- Uses conversational prompt validated through user testing
- Formatted with `format_review_content()` for uniform markdown

**Summary Contains:**

- Issue counts by severity (with emojis: 🔴 CRITICAL, 🟠 HIGH, etc.)
- Top 3-5 most critical issues with locations
- Brief recommendation on priorities
- Concise (1 page max, ~300-500 words)

**Configuration:**

- Enabled by default for full, summary, spaghetti, and security modes
- Disable with `--no-summary` flag for faster reviews
- Not available in expert mode (replaced by structured severity groupings)
- Token usage tracked and merged with main review

### 13. Expert Mode Architecture

Comprehensive two-stage review system with validation and false positive
filtering:

**Components:**

- `src/agent/expert/runner.py`: Orchestrates two-stage review process
- `src/agent/expert/primary_agent.py`: Stage 1 - comprehensive analysis
- `src/agent/expert/validation_agent.py`: Stage 2 - finding validation
- `src/agent/expert/schemas.py`: Pydantic models for structured output
- `src/agent/expert/renderer.py`: Markdown formatting for expert reviews
- `src/agent/expert/agent_factory.py`: Agent creation with consistent config
- `src/agent/expert/token_warning_injector.py`: Token usage monitoring

**New Tools:**

- `src/agent/tools/read_file.py`: Full file read with tracking (duplicate/
  consecutive read warnings)
- `src/agent/tools/search_in_files_locations.py`: Search returning Location
  objects

**Schemas (Pydantic):**

- `PrimaryReviewOutput`: Stage 1 output with ChangesSummary and ReviewFinding
  list
- `ReviewFinding`: Title, description, location list, recommendation, severity
- `ValidationOutput`: Stage 2 output with ValidatedReviewFinding list
- `ValidatedReviewFinding`: Extends ReviewFinding with confirmed flag and
  validation_reason
- `ExpertReviewResult`: Combined result with statistics and confirmed findings
- `Severity`: Enum (CRITICAL, HIGH, MEDIUM, LOW)
- `Location`: Code location (filepath, line_start, line_end)

**Workflow:**

1. **Stage 1 (Primary Review)**:
   - Agent receives context with changed files
   - Uses specialized tools (read_file, search_in_files_locations, etc.)
   - Generates structured PrimaryReviewOutput with findings
   - Token warning injector monitors usage and warns at thresholds (40%, 50%,
     60%, 70%, 80%, 85%, 90%, 95%)
   - If no findings, skip Stage 2
2. **Stage 2 (Validation)**:
   - Agent receives Stage 1 findings
   - Validates each finding using same tools
   - Confirms or rejects with reasoning
   - Generates ValidationOutput with validated findings
3. **Rendering**:
   - Filters to only confirmed findings
   - Groups by severity (CRITICAL → HIGH → MEDIUM → LOW)
   - Formats locations as file:line_start-line_end
   - Shows token usage for both stages
   - Logs statistics (confirmed/filtered counts) to console

**Key Features:**

- **False Positive Filtering**: Only validated findings appear in output
- **Token Monitoring**: Tracks cumulative token usage with configurable
  MAX_CONTEXT_WINDOW
- **Smart Tool Usage**: Warns about duplicate/consecutive reads to prevent
  inefficiency
- **Structured Output**: Pydantic schemas ensure consistent data structure
- **Graceful Degradation**: If Stage 2 fails, entire review fails (no partial
  results)
- **Agent Factory**: Centralizes agent creation with TokenWarningInjector
  middleware

**Testing:**

- `tests/agent/expert/test_runner.py`: End-to-end tests with mocked LLM
  responses
- `tests/agent/expert/test_token_warning_injector.py`: Token tracking and
  warning tests
- `tests/agent/tools/test_read_file.py`: Read tracking tests
- `tests/agent/tools/test_search_in_files_locations.py`: Location search tests
- `tests/test_token_usage.py`: TokenUsage dataclass tests

**Configuration:**

- `MAX_CONTEXT_WINDOW`: Expert mode only, controls token warning thresholds
  (default: 200000)
- No support for `--instructions` or `--no-summary` flags in expert mode

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
│       ├── expert/                      # Expert mode two-stage review
│       │   ├── __init__.py              # Expert mode exports
│       │   ├── runner.py                # Two-stage orchestrator
│       │   ├── primary_agent.py         # Stage 1: Primary review
│       │   ├── validation_agent.py      # Stage 2: Validation
│       │   ├── schemas.py               # Pydantic models
│       │   ├── renderer.py              # Markdown rendering
│       │   ├── agent_factory.py         # Agent creation helper
│       │   └── token_warning_injector.py # Token monitoring
│       ├── prompts/                     # Review prompts
│       │   ├── __init__.py              # Prompt loader
│       │   ├── full_review.md           # Full review mode prompt
│       │   ├── summary_mode.md          # Summary mode prompt
│       │   ├── spaghetti_code_detection.md  # Spaghetti mode prompt
│       │   ├── security_review.md       # Security mode prompt
│       │   ├── executive_summary.md     # Executive summary prompt
│       │   ├── context_summary.md       # Context compaction prompt
│       │   ├── expert_primary_review.md # Expert Stage 1 prompt
│       │   ├── expert_validation.md     # Expert Stage 2 prompt
│       │   ├── token_warning.md         # Token warning message
│       │   ├── duplicate_read_warning.md    # Duplicate read warning
│       │   └── consecutive_read_warning.md  # Consecutive read warning
│       ├── schema.py                    # Context model
│       ├── token_usage.py               # TokenUsage dataclass
│       ├── formatter.py                 # Markdown formatting utilities
│       ├── runner.py                    # Agent runner + summarize_review()
│       ├── progress_callback_handler.py # Progress display
│       └── tools/                       # 8 review tools
│           ├── changed_files.py         # List changed files
│           ├── get_commit_messages.py   # Get commit history
│           ├── diff_file.py             # Show git diff
│           ├── read_file_part.py        # Read file with line ranges
│           ├── read_file.py             # Read full file (expert)
│           ├── list_files.py            # List repository files
│           ├── search_in_files.py       # Search with context
│           └── search_in_files_locations.py  # Search locations (expert)
│
├── tests/                         # Integration tests
│   └── agent/
│       ├── expert/                # Expert mode tests
│       │   ├── test_runner.py     # End-to-end tests
│       │   └── test_token_warning_injector.py
│       └── tools/                 # Test per tool
│
└── spec/                          # Documentation
    ├── project-description.md
    ├── tools-specification.md
    └── implementation-summary.md  (this file)
```

______________________________________________________________________

## Implemented Tools

**Standard Tools (all modes):**

1. **changed_files** - List changed files
2. **get_commit_messages** - Get commit history
3. **diff_file** - Show git diff with pagination
4. **read_file_part** - Read file content with line ranges
5. **search_in_files** - Search patterns with context
6. **list_files** - List repository files

**Expert Mode Tools:**

7. **read_file** - Read entire file with duplicate/consecutive read tracking
8. **search_in_files_locations** - Search returning Location objects (no
   context)

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
poetry run reviewcerberus --mode security   # OWASP Top 10 security
poetry run reviewcerberus --mode expert     # Two-stage with validation

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
