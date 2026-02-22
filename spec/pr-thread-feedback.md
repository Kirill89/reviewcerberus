# PR Thread Feedback — Intelligent Issue Retention

## Context

ReviewCerberus resolves all old threads and creates fresh ones on every re-run.
User feedback (replies to bot comments) is lost. We want the bot to:

1. Remember previous issues and user replies
2. Decide which old issues are still valid (retained) vs. should be dropped
3. Only generate structured output for **new** issues (not re-describe retained
   ones)
4. See what code changed since each issue was originally found

Feedback is passed via a new `--feedback` CLI flag (separate from
`--instructions`). The Python schema gets one new output field:
`retained_issues: list[str]`.

## Design

### Issue lifecycle

```
Run 1:
  LLM → issues (each gets a UUID from the action)
  Action posts comments: <!-- reviewcerberus-issue:abc123:commitSHA -->

Run 2:
  Action fetches old threads → extracts issue ID, commit, user replies
  Action computes diff since original commit for affected files
  Action passes all this as --feedback to the LLM
  LLM → { issues: [new only], retained_issues: ["abc123"] }
  Action resolves threads NOT in retained list (and without user replies)
  Action keeps threads in retained list OR with user replies
  Action posts new comments for new issues
```

### What the LLM receives (in system prompt via --feedback)

```markdown
## Previous Review Issues

Below are issues from a previous review run. For each issue, you can see:
- The original finding (title, category, severity, location)
- Any replies from the PR author
- What changed in the affected file since the issue was found

For each previous issue, decide whether it should be RETAINED or DROPPED:
- RETAIN if: the issue is still present in the code, regardless of user replies
- DROP if: the code was fixed, or the author explained why it's not an issue
  and their reasoning is sound
- If the author said "fixed" but the code didn't change, RETAIN the issue

Add retained issue IDs to the `retained_issues` array in your output.
Do NOT re-describe retained issues in the `issues` array — only report
genuinely NEW findings there.

---

### Issue abc123
**Title:** Unused variable
**Category:** QUALITY | **Severity:** LOW
**File:** `app.py` (line 2)
**Found at commit:** 6a0cb09

**Author reply (@developer):**
> This is intentional for debugging

**Changes to `app.py` since 6a0cb09:**
(no changes)

---
```

### Comment marker format

Current: `<!-- reviewcerberus-issue -->` New:
`<!-- reviewcerberus-issue:ISSUE_ID:COMMIT_SHA -->`

Where:

- `ISSUE_ID` = 8-char random hex (crypto.randomUUID().slice(0,8))
- `COMMIT_SHA` = the PR head commit SHA at time of posting

## Implementation

### Step 1: Update comment marker (`action/src/render.ts`)

- `renderLineComment()` gains `issueId` and `commitSha` params
- Marker becomes `<!-- reviewcerberus-issue:ISSUE_ID:COMMIT_SHA -->`
- Existing `MARKER_ISSUE` detection still works (`.includes()`)
- Add `parseIssueMarker(body)` helper → `{ issueId, commitSha } | null`

### Step 2: Expand GraphQL query (`action/src/github.ts`)

- `comments(first: 1)` → `comments(first: 20)`
- Add `path`, `line`, `author { login }` to the query
- Update `ReviewThread` interface to include these fields

### Step 3: Thread classification (`action/src/feedback.ts` — new file)

`classifyThreads(threads)` → `ClassifiedThread[]`

Each `ClassifiedThread` contains: threadId (GraphQL), issueId (from marker),
commitSha, path, line, isResolved, botComment, userReplies, hasUserReply.

Logic:

- Filter to threads where first comment contains `MARKER_ISSUE`
- Parse `issueId` and `commitSha` from marker
- First comment author = bot; any other author = user reply
- Threads without parseable markers (old format) → treat as no-ID, resolve
  normally

### Step 4: Build feedback content (`action/src/feedback.ts`)

`buildFeedbackInstructions(classified, workspace)` → markdown string

For each classified thread with a valid issueId:

1. Extract title/category/severity from bot comment markdown
2. Compute diff since original commit: `git diff <commitSha>..HEAD -- <path>`
3. Format as the markdown block shown in the design section above

Returns empty string if no previous issues.

### Step 5: Wire feedback into review flow (`action/src/index.ts`)

New flow (replacing lines 51-105):

```
1. Fetch + classify threads
2. Build feedback content (includes git diffs)
3. Write feedback file to workspace
4. Run review (with --feedback flag + existing --instructions if any)
5. Parse retained_issues from output
6. Selective resolution:
   - Resolve threads NOT retained AND NOT having user replies
   - Keep threads that ARE retained OR have user replies
7. Post summary + new issue comments (with IDs + commit SHA in markers)
8. Clean up feedback file
```

The feedback file:

- Write feedback markdown to `.reviewcerberus-feedback.md` in workspace
- Pass as `--feedback /repo/.reviewcerberus-feedback.md` to Docker
- `--instructions` remains separate (user-provided instructions, unchanged)
- Clean up feedback file after review completes

### Step 6: Add `--feedback` flag to Python CLI

- **`src/main.py`** — add `--feedback` argument, read file content, pass to
  `run_review()`
- **`src/agent/runner.py`** — accept `thread_feedback` param, pass to
  `build_review_system_prompt()`
- **`src/agent/agent.py`** — thread `thread_feedback` through to
  `build_review_system_prompt()`
- **`src/agent/prompts/__init__.py`** — append feedback to system prompt

Prompt ordering: base prompt → SAST guidance → **thread feedback** → user
instructions (user instructions last = highest precedence).

### Step 7: Add `--feedback` to Docker args (`action/src/review.ts`)

Add `feedback?: string` to `ReviewConfig`. When set, push `--feedback <path>` to
Docker args.

### Step 8: Update Python schema (`src/agent/schema.py`)

Add `retained_issues: list[str]` field (default empty) to `PrimaryReviewOutput`.

### Step 9: Update system prompt (`src/agent/prompts/full_review.md`)

Add `retained_issues` to the OUTPUT REQUIREMENTS section — array of issue ID
strings for previous issues that are still valid.

### Step 10: Update review output parsing (`action/src/types.ts`)

Add `retained_issues?: string[]` to `ReviewOutput` interface.

### Step 11: Update act-test mock

**`act-test/github-routes.ts`**: Return a thread with a user reply and the new
marker format so the full flow is exercised.

**`act-test/fixtures/review-output.json`**: Add `retained_issues` field.

**`act-test/verify.test.ts`**: Add assertions:

- Thread with user reply is NOT resolved
- LLM system prompt contains "Previous Review Issues"
- New comments include issue ID in marker

## Files changed

### New files

| File | Purpose |
| -- | -- |
| `action/src/feedback.ts` | Thread classification + feedback instruction builder |
| `action/__tests__/feedback.test.ts` | Unit tests for classification and feedback |

### Modified files

| File | Change |
| -- | -- |
| `action/src/github.ts` | Expand GraphQL query (comments, path, line, author) |
| `action/src/render.ts` | Issue ID + commit SHA in markers; marker parser |
| `action/src/index.ts` | New flow: classify → feedback → review → selective resolve |
| `action/src/review.ts` | Add `feedback` to `ReviewConfig`, pass `--feedback` to Docker |
| `action/src/types.ts` | Add `retained_issues` to `ReviewOutput` |
| `src/main.py` | Add `--feedback` CLI flag |
| `src/agent/runner.py` | Thread `thread_feedback` parameter through |
| `src/agent/agent.py` | Thread `thread_feedback` parameter through |
| `src/agent/prompts/__init__.py` | Append feedback to system prompt (before instructions) |
| `src/agent/schema.py` | Add `retained_issues` field to `PrimaryReviewOutput` |
| `src/agent/prompts/full_review.md` | Document `retained_issues` in output requirements |
| `act-test/github-routes.ts` | Mock thread with user reply + new marker format |
| `act-test/fixtures/review-output.json` | Add `retained_issues` to mock output |
| `act-test/verify.test.ts` | New assertions for feedback flow |

### NOT changed

| File | Why |
| -- | -- |
| `action/action.yml` | No new inputs — feedback is automatic |
| `Dockerfile` | No changes |

## Edge cases

| Scenario | Behavior |
| -- | -- |
| First run (no old threads) | No feedback section, normal review |
| Old threads with old marker format (no ID) | Resolved normally (backward compat) |
| User reply + code changed | LLM sees the diff and decides |
| User reply + code unchanged | LLM sees empty diff, respects feedback |
| User said "fixed" + code unchanged | LLM sees empty diff, retains issue |
| retained_issues contains unknown ID | Ignored (thread already resolved or doesn't exist) |
| No retained_issues in output | All old threads resolved (except those with user replies) |
| Thread with user reply but NOT retained | Kept open anyway (user engagement preserved) |

## Verification

```bash
cd action && npm test          # unit tests including feedback.test.ts
cd action && npm run build     # rebuild dist
make test                      # full suite including act e2e
```
