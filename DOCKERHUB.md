# ReviewCerberus

AI-powered code review tool that analyzes git branch differences and generates
comprehensive review reports with executive summaries.

## Quick Start

```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --output /repo/review.md
```

**That's it!** The review will be saved to `review.md` in your current
directory.

## Key Features

- **Two Operation Modes**: Basic (single agent, fast) and Expert (multiple
  specialized agents, thorough, ~10x cost)
- **Executive Summaries**: Auto-generated highlights of critical issues
- **Multi-Provider**: AWS Bedrock, Anthropic API, or Ollama
- **Smart Analysis**: Token-efficient tools with prompt caching
- **Git Integration**: Works with any repository, supports commit hashes

## Usage Examples

Basic mode (default, single agent):

```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --output /repo/review.md
```

Expert mode (multiple specialized agents, ~10x cost):

```bash
# Recommended: Use cheaper models like Haiku for expert mode
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  -e MODEL_NAME=claude-haiku-4-5-20251001 \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --mode expert --output /repo/review.md
```

Custom target branch:

```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --target-branch develop --output /repo/review.md
```

Skip executive summary (faster, basic mode only):

```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --skip-summary --output /repo/review.md
```

## Operation Modes

### Basic Mode (Default)

**Single comprehensive agent** for fast, cost-effective reviews:

- **Speed**: Fast, completes in one agent run
- **Cost**: Standard model costs (~1x baseline)
- **Scope**: Covers all review aspects (logic, security, performance, quality,
  testing)
- **Best for**: Most code reviews, quick feedback, cost-sensitive projects

```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --output /repo/review.md
```

### Expert Mode

**Multiple specialized agents** running in parallel for thorough analysis:

- **Speed**: Slower, runs 8+ specialized agents concurrently
- **Cost**: ~10x more expensive due to multiple agents
- **Scope**: Each agent focuses on specific domain (security, performance, etc.)
- **Best for**: Critical reviews, security audits, architectural decisions

**⚠️ Cost Warning**: Expert mode runs multiple agents in parallel, consuming
significantly more tokens. We **strongly recommend using cheaper models** like
Claude Haiku to balance thoroughness with cost.

**Specialized Agents**: Security, Code Quality, Performance, Architecture,
Documentation, Error Handling, Business Logic, Testing

```bash
# Recommended: Use Haiku for expert mode
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  -e MODEL_NAME=claude-haiku-4-5-20251001 \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --mode expert --output /repo/review.md

# Or with Bedrock
docker run --rm -it -v $(pwd):/repo \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e AWS_REGION_NAME=us-east-1 \
  -e MODEL_NAME=us.anthropic.claude-haiku-4-5-20251001-v1:0 \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --mode expert --output /repo/review.md
```

**Control Agents**: Disable specific agents with flags:

```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --mode expert --no-documentation --no-testing \
  --output /repo/review.md
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

## Configuration

### Anthropic API

```bash
-e MODEL_PROVIDER=anthropic
-e ANTHROPIC_API_KEY=sk-ant-your-api-key
-e MODEL_NAME=claude-sonnet-4-5-20250929  # optional
```

### AWS Bedrock (default)

```bash
-e AWS_ACCESS_KEY_ID=your_key
-e AWS_SECRET_ACCESS_KEY=your_secret
-e AWS_REGION_NAME=us-east-1
-e MODEL_NAME=us.anthropic.claude-sonnet-4-5-20250929-v1:0  # optional
```

### Ollama (local models)

```bash
-e MODEL_PROVIDER=ollama
-e OLLAMA_BASE_URL=http://host.docker.internal:11434
-e MODEL_NAME=devstral-small-2:24b-cloud  # optional
```

## Command-Line Options

- `--mode`: Operation mode (`basic`, `expert`) - default: `basic`
- `--target-branch`: Branch to compare against - default: `main`
- `--output`: Output file path or directory
- `--repo-path`: Path to git repository - default: `/repo`
- `--instructions`: Path to markdown file with custom review guidelines
- `--skip-summary`: Skip executive summary generation (basic mode only)
- `--no-*`: Disable specific agents in expert mode (e.g., `--no-security`,
  `--no-testing`)

## Requirements

- Git repository mounted to `/repo`
- Either Anthropic API key or AWS Bedrock credentials
- Output directory must be writable

## Links

- Documentation: https://github.com/kirill89/reviewcerberus
- Issues: https://github.com/kirill89/reviewcerberus/issues

## License

MIT
