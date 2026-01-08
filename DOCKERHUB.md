# ReviewCerberus

AI-powered code review tool that analyzes git branch differences and generates
comprehensive review reports with structured output.

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

- **Comprehensive Reviews**: Detailed analysis of logic, security, performance,
  and code quality
- **Structured Output**: Issues organized by severity with summary table
- **Multi-Provider**: AWS Bedrock, Anthropic API, or Ollama
- **Smart Analysis**: Context provided upfront with prompt caching
- **Git Integration**: Works with any repository, supports commit hashes

## Usage Examples

Custom target branch:

```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --target-branch develop --output /repo/review.md
```

With custom review guidelines:

```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --instructions /repo/guidelines.md --output /repo/review.md
```

## What's Included

### Comprehensive Code Review

Detailed analysis covering:

- Logic & Correctness: Bugs, edge cases, error handling
- Security: OWASP issues, access control, input validation
- Performance: N+1 queries, bottlenecks, scalability
- Code Quality: Duplication, complexity, maintainability
- Side Effects: Impact on other system parts
- Testing: Coverage gaps, missing test cases
- Documentation: Missing or outdated docs

### Structured Output

Every review includes:

- **Summary**: High-level overview of changes and risky areas
- **Issues Table**: All issues at a glance with severity indicators (🔴 CRITICAL,
  🟠 HIGH, 🟡 MEDIUM, 🟢 LOW)
- **Detailed Issues**: Each issue with explanation, location, and suggested fix

## Configuration

### Anthropic API

```bash
-e MODEL_PROVIDER=anthropic
-e ANTHROPIC_API_KEY=sk-ant-your-api-key
-e MODEL_NAME=claude-opus-4-5-20251101  # optional
```

### AWS Bedrock (default)

```bash
-e AWS_ACCESS_KEY_ID=your_key
-e AWS_SECRET_ACCESS_KEY=your_secret
-e AWS_REGION_NAME=us-east-1
-e MODEL_NAME=us.anthropic.claude-opus-4-5-20251101-v1:0  # optional
```

### Ollama (local models)

```bash
-e MODEL_PROVIDER=ollama
-e OLLAMA_BASE_URL=http://host.docker.internal:11434
-e MODEL_NAME=deepseek-v3.1:671b-cloud  # optional
```

## Command-Line Options

- `--target-branch`: Branch to compare against - default: `main`
- `--output`: Output file path or directory
- `--repo-path`: Path to git repository - default: `/repo`
- `--instructions`: Path to markdown file with custom review guidelines

## Requirements

- Git repository mounted to `/repo`
- Either Anthropic API key or AWS Bedrock credentials
- Output directory must be writable

## Links

- Documentation: https://github.com/kirill89/reviewcerberus
- Issues: https://github.com/kirill89/reviewcerberus/issues

## License

MIT
