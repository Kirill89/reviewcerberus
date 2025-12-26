# ReviewCerberus

AI-powered code review tool that analyzes git branch differences and generates comprehensive review reports with executive summaries.

## Quick Start

```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --output /repo/review.md
```

**That's it!** The review will be saved to `review.md` in your current directory.

## Key Features

- **Four Review Modes**: Full (comprehensive), Summary (high-level), Spaghetti (code quality), Security (OWASP Top 10)
- **Executive Summaries**: Auto-generated highlights of critical issues
- **Multi-Provider**: AWS Bedrock or Anthropic API
- **Smart Analysis**: Token-efficient tools with prompt caching
- **Git Integration**: Works with any repository, supports commit hashes

## Usage Examples

Choose review mode:
```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --mode full --output /repo/review.md
```

Custom target branch:
```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --target-branch develop --output /repo/review.md
```

Skip executive summary (faster):
```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-your-api-key \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --no-summary --output /repo/review.md
```

## Review Modes

### Full Review (Comprehensive Analysis)
- Logic & Correctness: Bugs, edge cases, error handling
- Security: OWASP issues, access control, input validation
- Performance: N+1 queries, bottlenecks, scalability
- Code Quality: Duplication, complexity, maintainability
- Side Effects: Impact on other system parts
- Testing: Coverage gaps, missing test cases

### Summary Mode (High-Level Overview)
- Brief description of changes (2-4 sentences)
- Task-style description and logical grouping
- User impact and new components
- System integration overview

### Spaghetti Mode (Code Quality Analysis)
- Code Duplication: Within changes and across codebase
- Reuse Opportunities: Existing functions/classes to leverage
- Redundancy: Repeated checks and validations
- Library Usage: Standard library or dependency suggestions
- Abstraction: Opportunities for better patterns
- Dead Code: Unused imports, unreachable code
- Over-Engineering: Unnecessary complexity

### Security Mode (OWASP Top 10 Analysis)
- Access Control: Missing authorization, privilege escalation
- Cryptographic Failures: Hardcoded secrets, weak encryption
- Injection: Command, SQL, Path Traversal, Code Injection
- Authentication & Authorization: Weak auth, session issues
- Security Misconfiguration: Debug mode, verbose errors
- Vulnerable Components: Outdated dependencies
- Data Integrity: Insecure deserialization
- Logging & Monitoring: Missing security logs
- SSRF: Unvalidated URL requests

**Key Feature**: Actively traces data flows from user input to dangerous sinks to confirm exploitability, not just pattern matching.

### Executive Summary (All Modes)
Every review includes an auto-generated summary at the top:
- Top 3-5 critical issues with locations
- Issue counts by severity (🔴 CRITICAL, 🟠 HIGH, 🟡 MEDIUM, ⚪ LOW)
- Actionable recommendations

Disable with `--no-summary` for faster reviews.

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

- `--mode`: Review mode (`full`, `summary`, `spaghetti`, `security`) - default: `full`
- `--target-branch`: Branch to compare against - default: `main`
- `--output`: Output file path or directory
- `--repo-path`: Path to git repository - default: `/repo`
- `--instructions`: Path to markdown file with custom review guidelines
- `--no-summary`: Skip executive summary generation

## Requirements

- Git repository mounted to `/repo`
- Either Anthropic API key or AWS Bedrock credentials
- Output directory must be writable

## Links

- Documentation: https://github.com/kirill89/reviewcerberus
- Issues: https://github.com/kirill89/reviewcerberus/issues

## License

MIT
