# GitHub Action Implementation Plan

## Overview

Make ReviewCerberus work as a GitHub Action that runs on PRs, posts a summary
comment, and creates review comments on specific lines for each issue.

______________________________________________________________________

## Decisions Summary

| Question | Decision |
| -- | -- |
| Re-runs behavior | Update existing (resolve old threads, update summary) |
| Providers | All providers (expose all env vars/flags as inputs) |
| Issues without line number | File-level comment; enforce ≥1 location in schema |
| Exit code | Always succeed (for now) |
| Filtering | Min confidence level when `--verify` is enabled |

______________________________________________________________________

## Architecture

### Design Principle

**The GitHub Action is a completely isolated JavaScript wrapper around the
CLI.** No changes to Python code. The action:

1. Runs the Docker image with `--json` flag
2. Parses JSON output
3. Posts comments to GitHub using Octokit

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GitHub Action (JavaScript)                                                  │
│                                                                             │
│  • Native Node.js action (using: "node20") - fast startup                   │
│  • Runs Docker image via @actions/exec                                      │
│  • Uses @actions/github (Octokit) for GitHub API                            │
│  • Filtering logic (min_confidence) lives here                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Docker Image (kirill89/reviewcerberus)                                  │
│                                                                             │
│  docker run kirill89/reviewcerberus --json --target-branch main         │
│  → outputs JSON to stdout                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Components

```
action/
├── action.yml          # GitHub Action definition
├── package.json        # Dependencies + scripts
├── package-lock.json   # Lock file (committed)
├── tsconfig.json
├── vitest.config.ts
├── eslint.config.js    # ESLint flat config
├── .prettierrc         # Prettier config
├── src/
│   ├── index.ts        # Entry point
│   ├── review.ts       # Run Docker image, parse output
│   ├── github.ts       # GitHub API (comments, reviews, threads)
│   └── render.ts       # Render issues to markdown
├── __tests__/
│   ├── render.test.ts  # Unit tests for rendering
│   └── review.test.ts  # Unit tests for filtering/parsing
└── dist/
    └── index.js        # Bundled output (committed to repo)
```

### Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GitHub Action Triggered (on: pull_request)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Run Docker image via @actions/exec                                       │
│    docker run -v $GITHUB_WORKSPACE:/repo \                                  │
│      -e MODEL_PROVIDER -e ANTHROPIC_API_KEY ... \                           │
│      kirill89/reviewcerberus --json --target-branch $BASE_REF           │
│    + optional: --verify, --instructions                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. Parse JSON and filter issues                                             │
│    - JSON.parse(stdout)                                                     │
│    - If min_confidence set: filter issues with confidence < threshold       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. Resolve old review threads                                               │
│    - octokit.graphql() to get threads with <!-- reviewcerberus-issue -->    │
│    - octokit.graphql() to resolve each thread                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. Create/Update summary comment                                            │
│    - octokit.rest.issues.listComments() to find by marker                   │
│    - octokit.rest.issues.updateComment() or createComment()                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. Create review with line comments                                         │
│    - octokit.rest.pulls.createReview() with comments array                  │
│    - Each comment has <!-- reviewcerberus-issue --> marker                  │
│    - Issues with line → line comment                                        │
│    - Issues without line → file-level comment                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

______________________________________________________________________

## action.yml

```yaml
name: "ReviewCerberus"
description: "AI-powered code review for pull requests"
author: "Kirill"
branding:
  icon: "eye"
  color: "orange"

inputs:
  # Provider selection
  model_provider:
    description: "Model provider: bedrock, anthropic, ollama, or moonshot"
    required: false
    default: "bedrock"

  # AWS Bedrock
  aws_access_key_id:
    description: "AWS Access Key ID (for Bedrock)"
    required: false
  aws_secret_access_key:
    description: "AWS Secret Access Key (for Bedrock)"
    required: false
  aws_region_name:
    description: "AWS Region (for Bedrock)"
    required: false
    default: "us-east-1"

  # Anthropic
  anthropic_api_key:
    description: "Anthropic API key"
    required: false

  # Ollama
  ollama_base_url:
    description: "Ollama base URL"
    required: false
    default: "http://localhost:11434"

  # Moonshot
  moonshot_api_key:
    description: "Moonshot API key"
    required: false
  moonshot_api_base:
    description: "Moonshot API base URL"
    required: false
    default: "https://api.moonshot.ai/v1"

  # Model settings
  model_name:
    description: "Model name (provider-specific)"
    required: false
  max_output_tokens:
    description: "Maximum tokens in response"
    required: false

  # Review settings
  verify:
    description: "Enable Chain-of-Verification"
    required: false
    default: "false"
  verify_model_name:
    description: "Model for verification (defaults to model_name)"
    required: false
  instructions:
    description: "Path to markdown file with additional instructions"
    required: false

  # Filtering
  min_confidence:
    description: "Minimum confidence score (1-10), issues with confidence >= this value are reported (requires verify)"
    required: false

  # Quality gate
  fail_on:
    description: "Fail the action if issues at or above this severity are found (critical, high, medium, low)"
    required: false

  # GitHub token (automatically provided)
  github_token:
    description: "GitHub token for API access"
    required: false
    default: ${{ github.token }}

runs:
  using: "node20"
  main: "dist/index.js"
```

The JavaScript action reads inputs via `@actions/core`:

```typescript
import * as core from "@actions/core";

const modelProvider = core.getInput("model_provider");
const anthropicApiKey = core.getInput("anthropic_api_key");
const verify = core.getInput("verify") === "true";
const minConfidence = parseInt(core.getInput("min_confidence")) || undefined;
// ...
```

And passes them as environment variables to the Docker container:

```typescript
// Read version from pyproject.toml (single source of truth)
function getVersion(): string {
  const pyproject = fs.readFileSync("pyproject.toml", "utf-8");
  const match = pyproject.match(/^version\s*=\s*"([^"]+)"/m);
  if (!match) throw new Error("Could not find version in pyproject.toml");
  return match[1];
}

const version = getVersion();
const outputFile = ".reviewcerberus-output.json";
const workspace = process.env.GITHUB_WORKSPACE!;

await exec.exec("docker", [
  "run",
  "--rm",
  "-v", `${workspace}:/repo`,
  "-e", `MODEL_PROVIDER=${modelProvider}`,
  "-e", `ANTHROPIC_API_KEY=${anthropicApiKey}`,
  // ... other env vars
  `kirill89/reviewcerberus:${version}`,
  "--json",
  "--output", `/repo/${outputFile}`,
  "--target-branch", baseBranch,
  ...(verify ? ["--verify"] : []),
  ...(instructions ? ["--instructions", instructions] : []),
]);

// Read output file from mounted volume
const reviewJson = fs.readFileSync(path.join(workspace, outputFile), "utf-8");
const review = JSON.parse(reviewJson);
```

**Versioning:** `pyproject.toml` is the single source of truth. The action reads
the version at runtime and uses the matching Docker image tag.

______________________________________________________________________

## Release Automation

Add a step to `docker-publish.yml` to create a git tag after Docker publish:

```yaml
- name: Create git tag
  run: |
    VERSION="v${{ steps.version.outputs.VERSION }}"
    if git rev-parse "$VERSION" >/dev/null 2>&1; then
      echo "Tag $VERSION already exists, skipping"
    else
      git config user.name "github-actions[bot]"
      git config user.email "github-actions[bot]@users.noreply.github.com"
      git tag -a "$VERSION" -m "Release $VERSION"
      git push origin "$VERSION"
      echo "Created tag $VERSION"
    fi
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

This ensures:

- Docker image `kirill89/reviewcerberus:1.2.0` and git tag `v1.2.0` are created
  together
- Users can reference the action as `@v1.2.0`
- Action reads version from `pyproject.toml` and pulls matching Docker image

______________________________________________________________________

## GitHub API Operations

All API calls via `@actions/github` (Octokit):

| Operation | Octokit Method |
| -- | -- |
| List PR comments | `octokit.rest.issues.listComments()` |
| Create PR comment | `octokit.rest.issues.createComment()` |
| Update PR comment | `octokit.rest.issues.updateComment()` |
| Create review | `octokit.rest.pulls.createReview()` |
| Resolve review threads | `octokit.graphql()` (no REST API for this) |

______________________________________________________________________

## Dependencies

```json
{
  "dependencies": {
    "@actions/core": "^2.0.2",
    "@actions/github": "^7.0.0",
    "@actions/exec": "^2.0.0"
  },
  "devDependencies": {
    "typescript": "^5.9.3",
    "@vercel/ncc": "^0.38.4",
    "vitest": "^4.0.17",
    "eslint": "^9.39.2",
    "@typescript-eslint/eslint-plugin": "^8.53.0",
    "@typescript-eslint/parser": "^8.53.0",
    "prettier": "^3.7.4"
  },
  "scripts": {
    "build": "ncc build src/index.ts -o dist",
    "test": "vitest run",
    "lint": "eslint src __tests__",
    "format": "prettier --write src __tests__",
    "format:check": "prettier --check src __tests__"
  }
}
```

______________________________________________________________________

## Testing

Unit tests with Vitest for pure functions:

```typescript
// __tests__/render.test.ts
import { describe, it, expect } from "vitest";
import { renderLineComment, renderSummaryComment } from "../src/render";

describe("renderLineComment", () => {
  it("includes marker", () => {
    const issue = {
      title: "Null check missing",
      severity: "HIGH",
      category: "LOGIC",
      explanation: "...",
      suggested_fix: "...",
    };
    const result = renderLineComment(issue);
    expect(result).toContain("<!-- reviewcerberus-issue -->");
  });

  it("includes severity emoji", () => {
    const issue = { severity: "CRITICAL", ... };
    expect(renderLineComment(issue)).toContain("🔴");
  });
});

// __tests__/review.test.ts
import { describe, it, expect } from "vitest";
import { filterByConfidence, parseReviewOutput } from "../src/review";

describe("filterByConfidence", () => {
  it("filters issues below threshold", () => {
    const issues = [
      { title: "A", confidence: 8 },
      { title: "B", confidence: 5 },
      { title: "C", confidence: 9 },
    ];
    const result = filterByConfidence(issues, 7);
    expect(result).toHaveLength(2);
    expect(result.map(i => i.title)).toEqual(["A", "C"]);
  });

  it("returns all issues when no threshold", () => {
    const issues = [{ confidence: 3 }, { confidence: 5 }];
    expect(filterByConfidence(issues, undefined)).toHaveLength(2);
  });
});
```

Run locally:

```bash
cd action
npm test          # run tests
npm run lint      # check linting
npm run format    # format code
```

______________________________________________________________________

## CI Workflow

Add `.github/workflows/action-ci.yml` to run tests on PRs:

```yaml
name: Action CI

on:
  push:
    branches: [main]
    paths: ["action/**"]
  pull_request:
    paths: ["action/**"]

jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: action

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: action/package-lock.json

      - run: npm ci
      - run: npm run format:check
      - run: npm run lint
      - run: npm test
      - run: npm run build

      - name: Check dist is up to date
        run: |
          git diff --exit-code dist/ || \
            (echo "dist/ is out of date. Run 'npm run build' and commit." && exit 1)
```

______________________________________________________________________

## Comment Markers

| Marker | Purpose |
| -- | -- |
| `<!-- reviewcerberus-summary -->` | Identify summary PR comment |
| `<!-- reviewcerberus-issue -->` | Identify line review comments |

**Handling issue locations:**

- Issue with file + line → line comment on that line
- Issue with file only (no line) → file-level comment

Note: Schema enforces `min_length=1` on location, so every issue has at least a
filename.

______________________________________________________________________

## Comment Rendering

### Summary Comment

```markdown
<!-- reviewcerberus-summary -->
# 🐕‍🦺 ReviewCerberus

## Summary

{description from PrimaryReviewOutput}

## Issues Summary

| # | Title | Category | Severity | Location |
|---|-------|----------|----------|----------|
| 1 | ... | ... | 🔴 CRITICAL | `src/main.py` |
| 2 | ... | ... | 🟠 HIGH | `src/utils.py` |

---
*Generated by [ReviewCerberus](https://github.com/Kirill89/reviewcerberus)*
```

### Line Comment

```markdown
<!-- reviewcerberus-issue -->
### 🔴 CRITICAL: {title}

**Category:** {category}

#### Explanation

{explanation}

#### Suggested Fix

{suggested_fix}
```

Reuse `render_issue()` from `render_structured_output.py` with minor adaptations
for the marker and format.

______________________________________________________________________

## Schema Change (Required)

Enforce at least one location per issue:

```python
# schema.py
class ReviewIssue(BaseModel):
    ...
    location: list[IssueLocation] = Field(
        min_length=1,  # Ensures every issue has at least a filename
        description="List of file locations where the issue occurs"
    )
```

______________________________________________________________________

## Implementation Steps

### Phase 1: Project Setup

1. Create `action/` directory structure
2. Initialize npm project with TypeScript
   ```bash
   cd action && npm init -y
   npm install @actions/core @actions/github @actions/exec
   npm install -D typescript @vercel/ncc
   ```

### Phase 2: Core Implementation

3. Implement `src/render.ts`:

   - `renderSummaryComment()` - full summary with table
   - `renderLineComment()` - single issue for line comment

4. Implement `src/review.ts`:

   - `getVersion()` - read from pyproject.toml
   - `runReview()` - run Docker image via `@actions/exec`
   - `filterByConfidence()` - filter issues by threshold

5. Implement `src/github.ts`:

   - `findSummaryComment()` - find by marker
   - `createOrUpdateSummary()` - create/update summary
   - `getReviewThreads()` - GraphQL query for threads
   - `resolveThreads()` - GraphQL mutation to resolve
   - `createReview()` - create review with line comments

### Phase 3: Testing

6. Write unit tests:

   - `__tests__/render.test.ts` - test rendering functions
   - `__tests__/review.test.ts` - test filtering, parsing

7. Configure `vitest.config.ts`

### Phase 4: Entry Point

8. Implement `src/index.ts`:
   - Read inputs via `@actions/core`
   - Get GitHub context from `@actions/github`
   - Orchestrate: run review → resolve threads → post comments

### Phase 5: Build & Bundle

09. Configure `tsconfig.json` and build script
10. Bundle with `@vercel/ncc` → `dist/index.js`
11. Create `action.yml`
12. Test with a real PR

### Phase 6: Documentation

13. Update README with GitHub Action usage
14. Add example workflow file

______________________________________________________________________

## Example Usage

```yaml
name: Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: write     # Required for resolving review threads (GraphQL mutation)
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for diff

      - uses: Kirill89/reviewcerberus/action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          verify: "true"
          min_confidence: "7"
```

### Example as Quality Gate

```yaml
- uses: Kirill89/reviewcerberus/action@v1
  with:
    model_provider: anthropic
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    fail_on: "high"
```

______________________________________________________________________

## File Changes Summary

| File | Change |
| -- | -- |
| `src/agent/schema.py` | Update (add min_length=1 to location) |
| `action/action.yml` | Create |
| `action/package.json` | Create |
| `action/package-lock.json` | Create (committed) |
| `action/tsconfig.json` | Create |
| `action/vitest.config.ts` | Create |
| `action/eslint.config.js` | Create |
| `action/.prettierrc` | Create |
| `action/src/index.ts` | Create |
| `action/src/review.ts` | Create |
| `action/src/github.ts` | Create |
| `action/src/render.ts` | Create |
| `action/__tests__/render.test.ts` | Create |
| `action/__tests__/review.test.ts` | Create |
| `action/dist/index.js` | Create (bundled, committed) |
| `.github/workflows/action-ci.yml` | Create |
| `.github/workflows/docker-publish.yml` | Update (add git tag step) |
| `.gitignore` | Update (add `action/node_modules/`) |
| `README.md` | Update |

**Note:** The action is a completely isolated JavaScript wrapper that calls the
existing Docker image. Only one Python change required (schema constraint).

______________________________________________________________________

## Q&A - Implementation Details

**Q1: What's the GraphQL query for resolving review threads?**

```graphql
mutation ResolveThread($threadId: ID!) {
  resolveReviewThread(input: { threadId: $threadId }) {
    thread {
      isResolved
    }
  }
}
```

To get thread IDs, query `pullRequest.reviewThreads` and match by comment body
containing the marker.

**Q2: What if LLM reports an issue on a line NOT in the diff?**

GitHub only allows review comments on lines in the diff. If a line is not in the
diff, fall back to a file-level comment (no `line` parameter, just `path`). If
that also fails, include the issue in the summary comment instead.

**Q3: Where does `commit_id` come from for `pulls.createReview()`?**

```typescript
const commitSha = context.payload.pull_request.head.sha;
```

**Q4: How to handle issues with multiple locations?**

Post a comment on the first location only. The comment body can mention other
locations: "Also affects: `file2.py:20`, `file3.py:45`"

**Q5: What if no issues are found?**

Post a summary comment saying "✅ No issues found" - this confirms the review ran
successfully and provides visibility.

**Q6: How to handle the `instructions` file path?**

It's relative to the repo root. Mount it into Docker:

```typescript
...(instructions ? [
  "-v", `${workspace}/${instructions}:/repo/${instructions}`,
  "--instructions", `/repo/${instructions}`
] : [])
```

Actually simpler: the whole workspace is already mounted at `/repo`, so just
pass the relative path: `--instructions ${instructions}`

**Q7: Should we clean up `.reviewcerberus-output.json`?**

No, leave it. It might be useful for debugging. GitHub Actions workspace is
ephemeral anyway.

**Q8: Should we define TypeScript interfaces for the JSON output?**

Yes, define interfaces in `src/types.ts`:

```typescript
interface IssueLocation {
  filename: string;
  line?: number;
}

interface ReviewIssue {
  title: string;
  category: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  location: IssueLocation[];
  explanation: string;
  suggested_fix: string;
  confidence?: number;  // present if --verify was used
  rationale?: string;   // present if --verify was used
}

interface ReviewOutput {
  description: string;
  issues: ReviewIssue[];
}
```

**Q9: What about Docker Hub rate limits?**

Anonymous pulls: 100 pulls/6 hours per IP. GitHub-hosted runners share IPs, so
this could be an issue for very popular repos. Solutions:

- Users can authenticate to Docker Hub in their workflow
- We could publish to GitHub Container Registry (ghcr.io) as alternative
- For now, document the limitation; most repos won't hit it

**Q10: Does GitHub API support file-level comments (no line number)?**

Yes! In `pulls.createReview()`, omit the `line` field and just provide `path`:

```typescript
{
  path: "src/main.py",
  body: "<!-- reviewcerberus-issue -->\n..."
  // no 'line' field = file-level comment
}
```

This creates a comment attached to the file but not a specific line.
