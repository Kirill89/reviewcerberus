# Plan: PR Thread Feedback + Action Testing Infrastructure

## Context

ReviewCerberus posts inline review comments on PRs. On re-runs, all old threads
are resolved and new ones created fresh — losing any user feedback. Users want
to reply to the bot's findings ("this isn't an issue because X") and have the
bot respect that on the next run.

**Key design decisions:**

- Collect thread conversations (bot finding + user replies) via GitHub GraphQL
  API **before** the review runs
- Format them as markdown and pass via `--instructions` to the Docker CLI
- The Python CLI already appends instructions to the system prompt as "##
  Additional Review Guidelines" — **no Python code changes needed**
- Include resolved threads that have user replies (feedback is still valuable)
- Merge with user-provided `--instructions` when both exist (feedback first,
  user instructions second)

This plan also sets up local integration testing infrastructure for the GitHub
Action using [`act`](https://github.com/nektos/act).

______________________________________________________________________

## Part 1: Action Testing Infrastructure

### Step 1.1: Configure `act`

**New file:** `.actrc`

```
-P ubuntu-latest=catthehacker/ubuntu:act-latest
```

**New file:** `action/__tests__/fixtures/pull_request_event.json`

Realistic PR event payload for `act -e`:

```json
{
  "action": "synchronize",
  "pull_request": {
    "number": 1,
    "head": { "sha": "abc123def", "ref": "feature-branch" },
    "base": { "ref": "main" }
  },
  "repository": {
    "owner": { "login": "test-owner" },
    "name": "test-repo"
  }
}
```

______________________________________________________________________

### Step 1.2: Add Dry-Run Mode

The action calls Docker (needs LLM API key) and GitHub API (needs real token +
real PR). Add `REVIEWCERBERUS_DRY_RUN` env var to enable local testing.

**`action/src/review.ts`** — when dry-run is set, `runReview()` returns a
fixture `ReviewOutput` with sample issues instead of running Docker.

**`action/src/github.ts`** — when dry-run is set, `getReviewThreads()` returns
mock thread data from `action/__tests__/fixtures/mock_threads.json` instead of
calling GitHub API. This exercises the full feedback pipeline without a real
token.

**`action/src/index.ts`** — when dry-run is set, skip writing GitHub API calls
(resolveOurThreads, createOrUpdateSummary, createReview) and log what would be
done. The read path (getReviewThreads -> feedback pipeline) still runs with
injected mock data.

**New file:** `action/__tests__/fixtures/mock_threads.json`

Contains realistic thread data: 2-3 threads with our marker, some with user
replies, some without, one resolved with a reply. Used by both dry-run mode and
Vitest tests.

______________________________________________________________________

### Step 1.3: Create Test Workflow for `act`

**New file:** `.github/workflows/test-act.yml`

```yaml
name: Act Integration Test

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  test-action:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: ./action
        with:
          model_provider: "anthropic"
          anthropic_api_key: "fake-key-for-testing"
        env:
          REVIEWCERBERUS_DRY_RUN: "true"
```

Validates: action.yml is valid, dist/index.js loads, input parsing works, the
feedback flow integrates correctly.

______________________________________________________________________

### Step 1.4: Add Vitest Tests for GitHub API Module

**New file:** `action/__tests__/github.test.ts`

Test `getReviewThreads()` and `resolveOurThreads()` with a mocked Octokit
object. Use `vi.fn()` to mock `octokit.graphql` and `octokit.rest.*` methods.

These functions are currently untested.

______________________________________________________________________

### Step 1.5: Add Makefile Target

**Modify:** `Makefile`

```makefile
act-test:
	cd action && npm run build
	act pull_request \
	  -e action/__tests__/fixtures/pull_request_event.json \
	  -W .github/workflows/test-act.yml \
	  --env REVIEWCERBERUS_DRY_RUN=true \
	  -s GITHUB_TOKEN=fake-token
```

______________________________________________________________________

### Step 1.6: Verify

```bash
brew install act             # if not installed
make act-test                # should complete without errors
cd action && npm test        # existing + new github.test.ts should pass
```

______________________________________________________________________

## Part 2: PR Thread Feedback Feature

### Step 2.1: Expand GraphQL Query

**Modify:** `action/src/github.ts`

Current query (`getReviewThreads`) fetches `comments(first: 1)` with only
`body`. Expand to fetch all comments with author info, plus thread path/line.

Updated `ReviewThread` interface:

```typescript
interface ReviewThreadComment {
  body: string;
  author: { login: string } | null;
}

interface ReviewThread {
  id: string;
  isResolved: boolean;
  path: string | null;
  line: number | null;
  comments: {
    nodes: ReviewThreadComment[];
  };
}
```

Updated GraphQL query:

```graphql
reviewThreads(first: 100) {
  nodes {
    id
    isResolved
    path
    line
    comments(first: 100) {
      nodes {
        body
        author { login }
      }
    }
  }
}
```

The existing `resolveOurThreads()` continues to work unchanged — it only reads
the first comment's body for the marker check.

______________________________________________________________________

### Step 2.2: Create Feedback Module

**New file:** `action/src/feedback.ts`

Pure functions + temp file helpers:

**`collectThreadFeedback(threads: ReviewThread[]): ThreadFeedback[]`**

- Filter to threads where first comment has `MARKER_ISSUE` (our threads)
- Filter to threads where `comments.nodes.length > 1` (has user replies)
- Include both resolved and unresolved threads (resolved with replies = valuable
  feedback)
- Extract the issue title from the bot comment markdown
  (`### EMOJI SEVERITY: Title`)

```typescript
interface ThreadFeedback {
  path: string | null;
  line: number | null;
  issueTitle: string;
  botComment: string;
  userReplies: Array<{
    author: string;
    body: string;
  }>;
}
```

**`formatFeedbackAsInstructions(feedback: ThreadFeedback[]): string`**

Returns empty string if no feedback. Otherwise produces:

```markdown
## Previous Review Feedback

The following are conversations from previous review runs on this PR.
Users have replied to some findings. Take their feedback into account:
- If a user explains why a finding is not an issue, do NOT re-report it
- If a user provides context that affects the assessment, adjust accordingly
- Apply user feedback broadly: if feedback on one finding implies other similar
  findings are also invalid, do not report those either
- You may still report genuinely new issues

### Thread: [issue title]
**File:** `path/to/file.py` (line 42)
**Bot finding:**
[truncated bot comment, ~500 chars max]
**Reply (@username):** [user reply]
**Reply (@another):** [another reply]
```

**`mergeInstructions(workspace, userInstructionsPath, feedbackText): string | undefined`**

- No feedback + no user instructions -> `undefined`
- Only user instructions -> return original path unchanged (no temp file)
- Feedback exists -> read user instructions file (if any), combine (feedback
  first, user instructions second), write to
  `${workspace}/.reviewcerberus-instructions.md`, return
  `.reviewcerberus-instructions.md` (relative path for Docker mount)

**`cleanupFeedbackFile(workspace): void`**

Delete `.reviewcerberus-instructions.md` if it exists. Called in `finally`
block.

______________________________________________________________________

### Step 2.3: Wire into `index.ts`

**Modify:** `action/src/index.ts`

Insert between git fetch (line 49) and config building (line 52):

```typescript
// Collect thread feedback for LLM context
const threads = await getReviewThreads(octokit, ctx);
const feedback = collectThreadFeedback(threads);
if (feedback.length > 0) {
  core.info(`Found ${feedback.length} thread(s) with user feedback`);
}
const feedbackText = formatFeedbackAsInstructions(feedback);

// Merge with user-provided instructions
const effectiveInstructions = mergeInstructions(
  workspace,
  inputs.instructions,
  feedbackText
);

// Build review config (instructions now includes feedback)
const config: ReviewConfig = {
  workspace,
  targetBranch,
  verify: inputs.verify,
  sast: inputs.sast,
  instructions: effectiveInstructions,
  env: dockerEnv,
};
```

Wrap review + GitHub API calls in try/finally for cleanup:

```typescript
try {
  const reviewOutput = await runReview(config);
  // ... existing filtering, commenting, fail_on ...
} finally {
  cleanupFeedbackFile(workspace);
}
```

______________________________________________________________________

### Step 2.4: Update `.gitignore`

Add `.reviewcerberus-instructions.md` so the temp file doesn't get committed.

______________________________________________________________________

## Part 3: Tests for the Feature

### Step 3.1: Unit Tests for Feedback Module

**New file:** `action/__tests__/feedback.test.ts`

**`collectThreadFeedback`:**

- Returns `[]` when no threads
- Returns `[]` when threads have no user replies (only bot comment)
- Returns `[]` when threads don't have our marker
- Collects threads with marker + user replies
- Extracts issue title from bot comment markdown
- Handles multiple user replies per thread
- Includes resolved threads that have user replies
- Handles null author gracefully (uses "unknown")

**`formatFeedbackAsInstructions`:**

- Returns empty string when no feedback
- Formats single thread with header, bot finding, user reply
- Formats multiple threads
- Truncates long bot findings to ~500 chars
- Includes file path and line info
- Omits line when null

**`mergeInstructions`:**

- Returns `undefined` when neither feedback nor user instructions exist
- Returns original user instructions path when no feedback
- Creates temp file with feedback when no user instructions
- Creates temp file with both merged (feedback first) when both exist
- Reads user instructions file content correctly

______________________________________________________________________

### Step 3.2: Integration Test for the Full Flow

**New file:** `action/__tests__/integration/feedback-flow.test.ts`

End-to-end test: mock thread data -> collectThreadFeedback ->
formatFeedbackAsInstructions -> mergeInstructions. Verify final instructions
file is well-formed and contains both feedback and user instructions.

______________________________________________________________________

### Step 3.3: Expand `github.test.ts`

Add tests for the expanded `getReviewThreads` query:

- Returns full comment list with author info
- Includes path and line fields
- Handles threads with null path/line

______________________________________________________________________

### Step 3.4: Rebuild and Smoke Test

```bash
cd action && npm test && npm run build
make act-test
```

______________________________________________________________________

## Files Summary

### New files (8)

| File | Purpose |
| -- | -- |
| `spec/pr-thread-feedback.md` | This specification |
| `action/src/feedback.ts` | Thread feedback collection, formatting, merging |
| `action/__tests__/feedback.test.ts` | Unit tests for feedback module |
| `action/__tests__/github.test.ts` | Tests for GitHub API functions (mocked Octokit) |
| `action/__tests__/integration/feedback-flow.test.ts` | Integration test for feedback flow |
| `action/__tests__/fixtures/pull_request_event.json` | Mock event payload for `act` |
| `action/__tests__/fixtures/mock_threads.json` | Mock thread data for dry-run + tests |
| `.actrc` | Default `act` configuration |

### Modified files (5)

| File | Change |
| -- | -- |
| `action/src/github.ts` | Expand GraphQL query: all comments, author, path, line |
| `action/src/index.ts` | Wire feedback collection before runReview(), add cleanup |
| `action/src/review.ts` | Add dry-run mode for `act` testing |
| `.gitignore` | Add `.reviewcerberus-instructions.md` |
| `Makefile` | Add `act-test` target |

### Also update

| File | Change |
| -- | -- |
| `action/dist/index.js` | Rebuild: `cd action && npm run build` |
| `spec/implementation-summary.md` | Document the new feature |

______________________________________________________________________

## Edge Cases

| Scenario | Behavior |
| -- | -- |
| No threads on PR | No feedback, instructions pass through unchanged |
| Threads without user replies | Skipped (no feedback to incorporate) |
| Resolved threads with user replies | Included (user feedback is still valuable) |
| User also provides `--instructions` | Both merged into temp file (feedback first, then user instructions) |
| Author is null (deleted account) | Use "unknown" as author name |
| Very large feedback (many threads) | Truncate bot comments to ~500 chars each |
| Temp file cleanup on error | `finally` block ensures cleanup |
| Dry-run mode | Injects fixture data, skips Docker + write API calls |
| First run on a PR (no prior review) | No threads with our marker, no feedback |

______________________________________________________________________

## Verification

1. `cd action && npm test` — all new + existing tests pass
2. `cd action && npm run build` — bundle builds
3. `cd action && npm run lint && npm run format:check` — passes
4. `make act-test` — act smoke test completes
5. Manual test: create a PR, run the action, reply to a thread, re-run the
   action, verify the replied issue is not re-reported
