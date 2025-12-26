# ReviewCerberus

<p align="center">
  <img src="logo_256.png" alt="ReviewCerberus Logo" width="256" />
</p>

AI-powered code review tool that analyzes git branch differences and generates
comprehensive review reports.

## Features

- **Multi-Provider Support**: Use AWS Bedrock or Anthropic API
- **Automated Code Review**: Uses AI to analyze code changes between branches
- **Multiple Review Modes**: Choose between comprehensive full review or
  high-level summary
- **Comprehensive Analysis**: Reviews logic, security, performance, code
  quality, and more
- **Token Efficient**: Smart tools for partial file reading, diff pagination,
  and search with prompt caching
- **Markdown Output**: Generates readable review reports
- **Git Integration**: Works with any git repository and supports commit hashes

## Quick Start (Docker - Recommended)

**For AWS Bedrock:**

```bash
docker run --rm -it -v $(pwd):/repo \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e AWS_REGION_NAME=us-east-1 \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --output /repo/review.md
```

**For Anthropic API:**

```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --output /repo/review.md
```

**With custom options:**

```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --target-branch develop --output /repo/review.md
```

**Generate a summary instead of full review:**

```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --mode summary --output /repo/summary.md
```

## Installation (Development)

If you want to modify or develop ReviewCerberus:

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
poetry run reviewcerberus
```

### Review Modes

Choose between different review modes:

**Full Review (default)** - Comprehensive code review with detailed analysis:

```bash
poetry run reviewcerberus --mode full
```

**Summary Mode** - High-level overview of changes:

```bash
poetry run reviewcerberus --mode summary
```

The summary mode provides a concise overview including:

- Brief description of changes
- Task-style description of what changed and why
- Logical grouping of changes
- User impact (if applicable)
- New components and system integration
- Call graphs for complex interactions

**Spaghetti Code Detection** - Code quality and redundancy analysis:

```bash
poetry run reviewcerberus --mode spaghetti
```

The spaghetti mode focuses on code quality and maintainability:

- Code duplication (in changes and across codebase)
- Opportunities to reuse existing functions/classes
- Redundant checks and validations
- Missing opportunities for abstraction
- Better library usage
- Dead or unreachable code
- Over-engineering and unnecessary complexity

### Custom Target Branch

Review against a different branch or commit hash:

```bash
poetry run reviewcerberus --target-branch develop
# or use a commit hash
poetry run reviewcerberus --target-branch abc123def
```

### Custom Output File

Specify output file location:

```bash
poetry run reviewcerberus --output my-review.md
```

Or specify a directory (filename will be auto-generated):

```bash
poetry run reviewcerberus --output /path/to/reviews/
```

### Review Different Repository

Review a repository outside current directory:

```bash
poetry run reviewcerberus --repo-path /path/to/repo
```

### Custom Instructions

Provide additional instructions to the reviewer:

```bash
poetry run reviewcerberus --instructions review-guidelines.md
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
poetry run reviewcerberus --mode full --target-branch main --output review.md --instructions guidelines.md
```

Generate a quick summary instead:

```bash
poetry run reviewcerberus --mode summary --target-branch main --output summary.md
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

**Note:** Output filenames are automatically sanitized. For example, branch
`feature/new-feature` generates `review_feature_new-feature.md`.

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

### Full Review Mode

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

### Summary Mode

Generated summary includes:

1. **Overview**: Concise 2-4 sentence summary
2. **Task Description**: What problem is solved and scope of changes
3. **Logical Change Groups**: Changes organized by purpose
4. **User Impact**: How changes affect end users (if applicable)
5. **New Components**: New additions and system integration
6. **Call Graph**: Interaction diagrams for complex workflows (if applicable)

### Spaghetti Code Detection Mode

Generated review includes:

1. **Code Quality Summary**: Overall assessment of code quality
2. **Detailed Findings**: Organized by category:
   - Code Duplication
   - Redundancy Issues
   - Missed Reuse Opportunities
   - Library Usage Optimization
   - Abstraction Opportunities
   - Dead Code Detection
   - Over-Engineering Concerns
3. **Prioritized Issue List**: With severity, location, impact, and concrete
   fixes

## Development

### Building Docker Image

To build the Docker image locally:

```bash
make docker-build
```

To build and push to Docker Hub (multi-platform):

```bash
make docker-build-push
```

The version is automatically read from `pyproject.toml`.

See [DOCKER.md](DOCKER.md) for detailed Docker build and publish instructions.

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
    ├── prompts/                     # Review prompts
    │   ├── full_review.md           # Full review mode prompt
    │   ├── summary_mode.md          # Summary mode prompt
    │   └── context_summary.md       # Context compaction prompt
    ├── schema.py                    # Data models
    ├── runner.py                    # Review execution
    ├── progress_callback_handler.py # Progress display
    └── tools/                       # Review tools (6 total)
        ├── helpers.py               # Shared utilities
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

### Review Prompts

Review prompts are stored as markdown files in `src/agent/prompts/`:

- `full_review.md` - Comprehensive code review prompt
- `summary_mode.md` - High-level summary prompt
- `context_summary.md` - Context compaction for large PRs

Customize these files to adjust review criteria and output format.

## Requirements

- Python 3.11+
- Git
- **One of the following AI providers:**
  - AWS Bedrock access with Claude models
  - Anthropic API key
- Poetry for dependency management

## License

MIT
