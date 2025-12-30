# ReviewCerberus

<p align="center">
  <img src="logo_256.png" alt="ReviewCerberus Logo" width="256" />
</p>

AI-powered code review tool that analyzes git branch differences and generates
comprehensive review reports with executive summaries.

## Key Features

- **Two Operation Modes**: Basic (single agent, fast) and Expert (multiple
  specialized agents, thorough)
- **Four Review Types**: Full (comprehensive), Summary (high-level), Spaghetti
  (code quality), Security (OWASP Top 10)
- **Executive Summaries**: Auto-generated highlights of critical issues
- **Multi-Provider**: AWS Bedrock, Anthropic API, or Ollama
- **Smart Analysis**: Token-efficient tools with prompt caching
- **Git Integration**: Works with any repository, supports commit hashes

______________________________________________________________________

## Quick Start

Run with Docker (recommended):

```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --output /repo/review.md
```

**That's it!** The review will be saved to `review.md` in your current
directory.

See [Configuration](#configuration) for AWS Bedrock setup and other options.

______________________________________________________________________

## Usage

### Basic Commands

```bash
# Default: basic mode (single agent, fast, lower cost)
poetry run reviewcerberus

# Expert mode: multiple specialized agents (thorough, ~10x cost)
# Recommended with cheaper models like Claude Haiku
poetry run reviewcerberus --mode expert

# Custom target branch
poetry run reviewcerberus --target-branch develop

# Custom output location
poetry run reviewcerberus --output /path/to/review.md
poetry run reviewcerberus --output /path/to/dir/  # Auto-generates filename

# Different repository
poetry run reviewcerberus --repo-path /path/to/repo

# Add custom review guidelines
poetry run reviewcerberus --instructions guidelines.md

# Skip executive summary (faster, basic mode only)
poetry run reviewcerberus --skip-summary
```

### Example Commands

```bash
# Expert mode review with custom guidelines
poetry run reviewcerberus --mode expert --target-branch main \
  --output review.md --instructions guidelines.md

# Basic mode for quick review
poetry run reviewcerberus --repo-path /other/repo

# Expert mode with specific agents disabled
poetry run reviewcerberus --mode expert --no-documentation --no-testing
```

______________________________________________________________________

## Operation Modes

### Basic Mode (Default)

**Single comprehensive agent** that performs complete code review:

- **Speed**: Fast, completes in one agent run
- **Cost**: Standard model costs (~1x baseline)
- **Scope**: Covers all review aspects in one analysis
- **Best for**: Most code reviews, quick feedback, cost-sensitive projects

### Expert Mode

**Multiple specialized agents** running in parallel for thorough analysis:

- **Speed**: Slower, runs 8+ specialized agents concurrently
- **Cost**: ~10x more expensive due to multiple agents
- **Scope**: Each agent focuses on specific domain (security, performance, etc.)
- **Best for**: Critical reviews, security audits, architectural decisions

**⚠️ Cost Warning**: Expert mode runs multiple agents in parallel, consuming
significantly more tokens. We recommend using cheaper models like Claude Haiku
to balance thoroughness with cost:

```bash
# Set in .env file:
MODEL_NAME=us.anthropic.claude-haiku-4-5-20251001-v1:0  # For Bedrock
# or
MODEL_NAME=claude-haiku-4-5-20251001  # For Anthropic API
```

**Specialized Agents**:

1. **Security**: OWASP Top 10, access control, injection vulnerabilities
2. **Code Quality**: Duplication, complexity, maintainability
3. **Performance**: Bottlenecks, N+1 queries, scalability issues
4. **Architecture**: Design patterns, coupling, modularity
5. **Documentation**: Code comments, README updates, API docs
6. **Error Handling**: Exception handling, error messages, recovery
7. **Business Logic**: Correctness, edge cases, business rules
8. **Testing**: Test coverage, missing test cases, test quality

**Control Agents**: Disable specific agents with flags:

```bash
poetry run reviewcerberus --mode expert --no-documentation --no-testing
```

Available flags: `--no-security`, `--no-code-quality`, `--no-performance`,
`--no-architecture`, `--no-documentation`, `--no-error-handling`,
`--no-business-logic`, `--no-testing`

### Executive Summary (Basic Mode Only)

Basic mode reviews include an auto-generated executive summary at the top:

- Top 3-5 critical issues with locations
- Issue counts by severity (🔴 CRITICAL, 🟠 HIGH, 🟡 MEDIUM, ⚪ LOW)
- Actionable recommendations

Disable with `--skip-summary` for faster reviews.

**Note**: Expert mode does not generate executive summaries, as the summary
agent already synthesizes findings from all specialized agents.

______________________________________________________________________

## How It Works

1. **Detects** current git branch and repository
2. **Compares** changes between current branch and target branch
3. **Analyzes** using AI agent with specialized tools:
   - List changed files
   - Read file contents with line ranges
   - View git diffs with pagination
   - Search patterns across codebase
   - Review commit messages
4. **Generates** markdown review report with executive summary

**Progress Display:**

```
Repository: /path/to/repo
Current branch: feature-branch
Target branch: main

Found 3 changed files:
  - src/main.py (modified)
  - src/utils.py (modified)
  - tests/test_main.py (added)

Starting code review...

🤔 Thinking... ⏱️  3.0s
🔧 changed_files
🔧 diff_file: src/main.py
📊 Generating executive summary...

✓ Review completed: review_feature-branch.md

Token Usage:
  Input tokens:  6,856
  Output tokens: 1,989
  Total tokens:  8,597
```

______________________________________________________________________

## Configuration

All configuration via environment variables (`.env` file):

### Provider Selection

```bash
MODEL_PROVIDER=bedrock  # or "anthropic" (default: bedrock)
```

### AWS Bedrock (if MODEL_PROVIDER=bedrock)

```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION_NAME=us-east-1
MODEL_NAME=us.anthropic.claude-sonnet-4-5-20250929-v1:0  # optional
```

**Docker example with Bedrock:**

```bash
docker run --rm -it -v $(pwd):/repo \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e AWS_REGION_NAME=us-east-1 \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --output /repo/review.md
```

### Anthropic API (if MODEL_PROVIDER=anthropic)

```bash
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
MODEL_NAME=claude-sonnet-4-5-20250929  # optional
```

### Ollama (if MODEL_PROVIDER=ollama)

```bash
MODEL_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434  # optional, default
MODEL_NAME=devstral-small-2:24b-cloud   # optional
```

**Docker example with Ollama:**

```bash
# Assumes Ollama running on host machine
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=ollama \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --output /repo/review.md
```

### Optional Settings

```bash
MAX_OUTPUT_TOKENS=8192      # Maximum tokens in response
RECURSION_LIMIT=200         # Agent recursion limit (basic mode)
RECURSION_LIMIT=600         # Agent recursion limit (expert mode, recommended)
```

### Model Recommendations

**For Expert Mode**: Use cheaper models to balance cost with thoroughness:

```bash
# Bedrock (recommended for expert mode)
MODEL_NAME=us.anthropic.claude-haiku-4-5-20251001-v1:0

# Anthropic API (recommended for expert mode)
MODEL_NAME=claude-haiku-4-5-20251001
```

**For Basic Mode**: Use more capable models for best single-agent performance:

```bash
# Bedrock
MODEL_NAME=us.anthropic.claude-sonnet-4-5-20250929-v1:0  # default

# Anthropic API
MODEL_NAME=claude-sonnet-4-5-20250929  # default
```

### Custom Review Prompts

Customize prompts in `src/agent/prompts/`:

- `basic_mode.md` - Basic mode comprehensive review
- `expert/` - Expert mode specialized agent prompts
- `executive_summary.md` - Executive summary generation
- `context_summary.md` - Context compaction for large PRs

______________________________________________________________________

## Development

### Local Installation

For local development (not required for Docker usage):

```bash
# Clone and install
git clone <repo-url>
poetry install

# Configure credentials
cp .env.example .env
# Edit .env with your provider credentials
```

See [Configuration](#configuration) for credential setup.

### Run Tests

```bash
make test
# or
poetry run pytest -v
```

### Linting & Formatting

```bash
make lint     # Check with mypy, isort, black, mdformat
make format   # Auto-format with isort and black
```

### Building Docker Image

```bash
make docker-build           # Build locally
make docker-build-push      # Build and push (multi-platform)
```

Version is auto-read from `pyproject.toml`. See [DOCKER.md](DOCKER.md) for
details.

### Project Structure

```
src/
├── config.py                        # Configuration
├── main.py                          # CLI entry point
└── agent/
    ├── agent.py                     # Agent setup
    ├── model.py                     # Model initialization
    ├── basic/                       # Basic mode (single agent)
    │   └── runner.py                # Review execution
    ├── expert/                      # Expert mode (multi-agent)
    │   ├── runner.py                # Multi-agent orchestration
    │   ├── schemas.py               # Structured outputs
    │   └── utils.py                 # Utilities
    ├── prompts/                     # Review prompts
    │   ├── basic_mode.md            # Basic mode prompt
    │   ├── expert/                  # Expert mode agent prompts (9 files)
    │   └── ...                      # Other prompts
    ├── callbacks/                   # Progress tracking
    ├── middleware/                  # Agent middleware
    ├── schema.py                    # Data models
    └── tools/                       # 6 review tools
```

### Code Quality Standards

- **Strict type checking**: All functions require type annotations
- **Return types**: Must be explicit (`warn_return_any = true`)
- **Formatting**: Black + isort with black profile
- **Testing**: Integration tests with real git operations

______________________________________________________________________

## Requirements

- Python 3.11+
- Git
- One of:
  - AWS Bedrock access with Claude models
  - Anthropic API key
- Poetry (for development)

______________________________________________________________________

## License

MIT
