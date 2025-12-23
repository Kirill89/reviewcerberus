# Review Bot

AI-powered code review tool that analyzes git branch differences and generates comprehensive review reports.

## Features

- **Multi-Provider Support**: Use AWS Bedrock or Anthropic API
- **Automated Code Review**: Uses AI to analyze code changes between branches
- **Comprehensive Analysis**: Reviews logic, security, performance, code quality, and more
- **Token Efficient**: Smart tools for partial file reading, diff pagination, and search with prompt caching
- **Markdown Output**: Generates readable review reports
- **Git Integration**: Works with any git repository

## Installation

1. Clone the repository
2. Install dependencies:
```bash
poetry install
```

3. Configure AI provider credentials in `.env`:
```bash
cp .env.example .env
# Edit .env with your credentials
```

**For AWS Bedrock (default):**
```
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION_NAME=us-east-1
```

**For Anthropic API:**
```
MODEL_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-api-key
MODEL_NAME=claude-sonnet-4-5-20250929
```

Optional configuration (defaults shown):
```
MAX_OUTPUT_TOKENS=8192
RECURSION_LIMIT=200
```

## Usage

### Basic Usage

Review current branch against `main`:
```bash
poetry run review-bot
```

### Custom Target Branch

Review against a different branch:
```bash
poetry run review-bot --target-branch develop
```

### Custom Output File

Specify output file location:
```bash
poetry run review-bot --output my-review.md
```

### Review Different Repository

Review a repository outside current directory:
```bash
poetry run review-bot --repo-path /path/to/repo
```

### Custom Instructions

Provide additional instructions to the reviewer:
```bash
poetry run review-bot --instructions review-guidelines.md
```

Example `review-guidelines.md`:
```markdown
# Additional Review Guidelines

- Focus on error handling in API endpoints
- Check for SQL injection vulnerabilities
- Verify all database queries use parameterized statements
- Ensure proper logging of security-related events
```

### Full Example

```bash
poetry run review-bot --target-branch main --output review.md --instructions guidelines.md
```

## How It Works

1. Detects current git branch and repository
2. Compares changes between current branch and target branch
3. AI agent uses specialized tools to:
   - List changed files
   - Read file contents
   - View git diffs with pagination
   - Search across codebase
   - Review commit messages
4. Generates comprehensive markdown review report

**Note:** Output filenames are automatically sanitized. For example, branch `feature/new-feature` generates `review_feature_new-feature.md`.

## Progress Visualization

The tool displays real-time progress:
```
Repository: /Users/kirill/Mobb/autofixer
Current branch: feature-branch
Target branch: main
Output file: review_feature-branch.md

Model provider: bedrock
Model: us.anthropic.claude-sonnet-4-5-20250929-v1:0

Found 3 changed files:
  - src/main.py (modified)
  - src/utils.py (modified)
  - tests/test_main.py (added)

Starting code review...

🤔 Thinking...
   ⏱️  3.0s
🔧 changed_files
🔧 get_commit_messages
🤔 Thinking...
   ⏱️  2.8s
🔧 diff_file: src/main.py
🤔 Thinking...
   ⏱️  4.2s

✓ Review completed and saved to: review_feature.md

Token Usage:
  Input tokens:  6,856
  Output tokens: 1,989
  Total tokens:  8,597
```

Shows:
- Thinking duration for each LLM call
- Tool calls with key parameters
- Total token usage (aggregated across all LLM calls)

## Review Dimensions

The AI reviews code across multiple dimensions:

- **Logic & Correctness**: Bugs, edge cases, error handling
- **Security**: OWASP issues, access control, input validation
- **Performance**: N+1 queries, bottlenecks, scalability
- **Code Quality**: Duplication, complexity, maintainability
- **Side Effects**: Impact on other parts of the system
- **Testing**: Test coverage, missing test cases

## Output Format

Generated review includes:

1. **Summary**: Overview of changes
2. **Key Changes**: Main features/modifications
3. **Positive Aspects**: What was done well
4. **Issues Found**: Prioritized list with:
   - Severity (CRITICAL, HIGH, MEDIUM, LOW)
   - Category
   - Location (file and function)
   - Problem description
   - Impact explanation
   - Suggested fix with code examples
5. **Recommendations**: General improvement suggestions

## Development

### Run Tests

```bash
make test
# or
poetry run pytest -v
```

### Linting

Check code quality with mypy, isort, and black:
```bash
make lint
```

### Format Code

Auto-format code with isort and black:
```bash
make format
```

The project enforces strict type checking:
- All functions require type annotations (`disallow_untyped_defs = true`)
- Return types must be explicit (`warn_return_any = true`)
- Imports are sorted consistently (isort with black profile)
- Code follows black formatting standards

### Project Structure

```
src/
├── config.py                        # Configuration (env vars)
├── main.py                          # CLI entry point
└── agent/
    ├── agent.py                     # Agent configuration
    ├── model.py                     # Model setup (Bedrock/Anthropic)
    ├── caching_bedrock_client.py    # Bedrock caching wrapper
    ├── caching_anthropic_client.py  # Anthropic caching wrapper
    ├── system.py                    # Review prompt
    ├── schema.py                    # Data models
    ├── runner.py                    # Review execution
    ├── progress_callback_handler.py # Progress display
    └── tools/                       # Review tools (6 total)
        ├── changed_files.py
        ├── read_file_part.py
        ├── diff_file.py
        ├── list_files.py
        ├── search_in_files.py
        └── get_commit_messages.py
```

## Tools Available to AI

The AI agent has access to specialized tools:

- **changed_files**: List all files changed between branches
- **get_commit_messages**: Understand intent from commit history
- **diff_file**: View git diff with hunk-based pagination (default: 20 hunks)
- **read_file_part**: Read specific lines or entire files
- **search_in_files**: Search patterns across codebase
- **list_files**: List repository files with pattern matching

## Configuration

All configuration is managed through environment variables in `.env`:

### Provider Selection
```bash
MODEL_PROVIDER=bedrock  # or "anthropic" (default: bedrock)
```

### AWS Bedrock Configuration (Required if MODEL_PROVIDER=bedrock)
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION_NAME=us-east-1
```

### Anthropic API Configuration (Required if MODEL_PROVIDER=anthropic)
```bash
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

### Model Configuration (Optional)
```bash
# AI model to use
# For Bedrock (default):
MODEL_NAME=us.anthropic.claude-sonnet-4-5-20250929-v1:0
# For Anthropic API:
# MODEL_NAME=claude-sonnet-4-5-20250929  # or claude-3-5-sonnet-20241022, etc.

# Maximum tokens in model response
MAX_OUTPUT_TOKENS=8192

# Agent recursion limit
RECURSION_LIMIT=200
```

### Review Prompt

Customize review criteria in `src/agent/system.py`.

## Requirements

- Python 3.11+
- Git
- **One of the following AI providers:**
  - AWS Bedrock access with Claude models
  - Anthropic API key
- Poetry for dependency management

## License

MIT
