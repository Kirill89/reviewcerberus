# ReviewCerberus

<p align="center">
  <img src="https://raw.githubusercontent.com/Kirill89/reviewcerberus/main/logo_256.png" alt="ReviewCerberus Logo" width="256" />
</p>

AI-powered code review tool that analyzes git branch differences and generates
comprehensive review reports with structured output.

## Key Features

- **GitHub Action**: Automated PR reviews with inline comments and summary
- **Comprehensive Reviews**: Detailed analysis of logic, security, performance,
  and code quality
- **Structured Output**: Issues organized by severity with summary table
- **Multi-Provider**: AWS Bedrock, Anthropic API, or Ollama
- **Smart Analysis**: Context provided upfront with prompt caching
- **Git Integration**: Works with any repository, supports commit hashes
- **Verification Mode**: Experimental
  [Chain-of-Verification](https://arxiv.org/abs/2309.11495) to reduce false
  positives

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

### GitHub Action

For automated PR reviews, add to `.github/workflows/review.yml`:

```yaml
name: Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: Kirill89/reviewcerberus@v1
        with:
          model_provider: anthropic
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

The action posts review comments directly on your PR. See
[GitHub Action](#github-action-1) for all options.

______________________________________________________________________

## Usage

### Basic Commands

```bash
# Run code review
poetry run reviewcerberus

# Custom target branch
poetry run reviewcerberus --target-branch develop

# Custom output location
poetry run reviewcerberus --output /path/to/review.md
poetry run reviewcerberus --output /path/to/dir/  # Auto-generates filename

# Output as JSON instead of markdown
poetry run reviewcerberus --json

# Different repository
poetry run reviewcerberus --repo-path /path/to/repo

# Add custom review guidelines
poetry run reviewcerberus --instructions guidelines.md

# Enable verification mode (experimental)
poetry run reviewcerberus --verify
```

### Example Commands

```bash
# Full review with custom guidelines
poetry run reviewcerberus --target-branch main \
  --output review.md --instructions guidelines.md

# Review a different repo
poetry run reviewcerberus --repo-path /other/repo
```

______________________________________________________________________

## What's Included

### Comprehensive Code Review

Detailed analysis covering:

- **Logic & Correctness**: Bugs, edge cases, error handling
- **Security**: OWASP issues, access control, input validation
- **Performance**: N+1 queries, bottlenecks, scalability
- **Code Quality**: Duplication, complexity, maintainability
- **Side Effects**: Impact on other system parts
- **Testing**: Coverage gaps, missing test cases
- **Documentation**: Missing or outdated docs, unclear comments

### Structured Output

Every review includes:

- **Summary**: High-level overview of changes and risky areas
- **Issues Table**: All issues at a glance with severity indicators (🔴 CRITICAL,
  🟠 HIGH, 🟡 MEDIUM, 🟢 LOW)
- **Detailed Issues**: Each issue with explanation, location, and suggested fix

### Verification Mode (Experimental)

Enable with `--verify` flag to reduce false positives using
[Chain-of-Verification (CoVe)](https://arxiv.org/abs/2309.11495):

1. **Generate Questions**: Creates falsification questions for each issue
2. **Answer Questions**: Answers questions using code context
3. **Score Confidence**: Assigns 1-10 confidence score based on evidence

Each issue in the output includes a confidence score and rationale.

______________________________________________________________________

## How It Works

1. **Detects** current git branch and repository
2. **Collects** all context upfront: changed files, commit messages, and diffs
3. **Analyzes** using AI agent with access to:
   - Full diff context (truncated at 10k chars per file)
   - File reading with line ranges
   - Pattern search across codebase
   - Directory listing
4. **Generates** structured review output rendered as markdown

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
🔧 read_file_part: src/main.py

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
MODEL_PROVIDER=bedrock  # or "anthropic" or "ollama" (default: bedrock)
```

### AWS Bedrock (if MODEL_PROVIDER=bedrock)

```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION_NAME=us-east-1
MODEL_NAME=us.anthropic.claude-opus-4-5-20251101-v1:0  # optional
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
MODEL_NAME=claude-opus-4-5-20251101  # optional
```

### Ollama (if MODEL_PROVIDER=ollama)

```bash
MODEL_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434  # optional, default
MODEL_NAME=deepseek-v3.1:671b-cloud     # optional
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
MAX_OUTPUT_TOKENS=10000     # Maximum tokens in response
RECURSION_LIMIT=200         # Agent recursion limit
VERIFY_MODEL_NAME=...       # Model for verification (defaults to MODEL_NAME)
```

### Custom Review Prompts

Customize prompts in `src/agent/prompts/`:

- `full_review.md` - Main review prompt
- `context_summary.md` - Context compaction for large PRs

______________________________________________________________________

## GitHub Action

Use ReviewCerberus as a GitHub Action for automated PR reviews.

### Action Inputs

| Input | Description | Default |
| -- | -- | -- |
| `model_provider` | Provider: `bedrock`, `anthropic`, or `ollama` | `bedrock` |
| `anthropic_api_key` | Anthropic API key | - |
| `aws_access_key_id` | AWS Access Key ID (Bedrock) | - |
| `aws_secret_access_key` | AWS Secret Access Key (Bedrock) | - |
| `aws_region_name` | AWS Region (Bedrock) | `us-east-1` |
| `model_name` | Model name (provider-specific) | - |
| `verify` | Enable Chain-of-Verification | `false` |
| `min_confidence` | Min confidence score 1-10 (requires verify) | - |
| `instructions` | Path to custom review guidelines | - |

### Example with Verification

```yaml
- uses: Kirill89/reviewcerberus@v1
  with:
    model_provider: anthropic
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    verify: "true"
    min_confidence: "7"
```

### Example with AWS Bedrock

```yaml
- uses: Kirill89/reviewcerberus@v1
  with:
    model_provider: bedrock
    aws_access_key_id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws_secret_access_key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws_region_name: us-east-1
```

### What the Action Does

1. Runs the review using the Docker image
2. Resolves any existing review threads from previous runs
3. Posts a summary comment with all issues
4. Creates inline review comments on specific lines

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
├── src/                             # Python CLI
│   ├── config.py                    # Configuration
│   ├── main.py                      # CLI entry point
│   └── agent/
│       ├── agent.py                 # Agent setup
│       ├── model.py                 # Model initialization
│       ├── runner.py                # Review execution
│       ├── prompts/                 # Review prompts
│       ├── schema.py                # Data models (structured output)
│       ├── git_utils/               # Git operations
│       ├── formatting/              # Context and output rendering
│       ├── verification/            # Chain-of-Verification pipeline
│       ├── progress_callback_handler.py
│       └── tools/                   # 3 review tools
│
└── action/                          # GitHub Action (TypeScript)
    ├── action.yml                   # Action definition
    ├── src/                         # Action source code
    └── dist/                        # Bundled action
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
