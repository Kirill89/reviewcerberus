# Verification Mode

## Overview

Verification mode (`--verify` flag) implements
[Chain-of-Verification (CoVe)](https://arxiv.org/abs/2309.11495) to reduce false
positives in code reviews. This is an experimental feature that adds a
multi-step verification pipeline after the primary review.

## Why Verification?

LLM-based code reviews can produce false positives - issues that appear valid
but are actually incorrect upon closer examination. CoVe addresses this by:

1. **Self-Verification**: The model questions its own findings
2. **Evidence-Based Scoring**: Each issue gets a confidence score based on
   concrete evidence
3. **Transparency**: Users see the rationale behind each confidence score

For more background on self-criticism techniques, see:
[Chain of Verification](https://learnprompting.org/docs/advanced/self_criticism/chain_of_verification)

______________________________________________________________________

## How It Works

### Pipeline Steps

**Step 1: Generate Falsification Questions**

For each issue from the primary review, generate questions that would disprove
the issue if answered affirmatively. These questions target the specific claims
made in the issue.

Example:

- Issue: "Null pointer dereference at line 42"
- Questions:
  - "Is the variable checked for null before line 42?"
  - "Is the variable guaranteed to be non-null from the caller?"

**Step 2: Answer Questions**

Answer each question using only the available code context (diffs, file content
read during review). Answers must be grounded in evidence from the code.

**Step 3: Score Confidence**

Based on the Q&A evidence, assign a confidence score (1-10) to each issue:

- 1-3: Low confidence (likely false positive)
- 4-6: Medium confidence (uncertain)
- 7-10: High confidence (likely valid issue)

Each score includes a rationale explaining the evidence.

______________________________________________________________________

## Architecture

```
src/agent/verification/
├── __init__.py           # Public exports
├── schema.py             # Pydantic models for structured output
├── agent.py              # LLM calls (3 agents, one per step)
├── runner.py             # Pipeline orchestration
└── helpers.py            # Pure transformation functions
```

### Key Components

**Schema** (`schema.py`):

- `QuestionsOutput`: Questions for each issue
- `AnswersOutput`: Answers with evidence
- `VerificationOutput`: Confidence scores and rationale
- `VerifiedReviewIssue`: Issue with confidence/rationale fields
- `VerifiedReviewOutput`: Final output with verified issues

**Agent** (`agent.py`):

- `generate_questions()`: Step 1 LLM call
- `answer_questions()`: Step 2 LLM call
- `score_issues()`: Step 3 LLM call

Each function uses `create_agent()` with `response_format` for structured
output.

**Runner** (`runner.py`):

- `run_verification()`: Main entry point
- Orchestrates steps 1-3
- Tracks token usage across all steps
- Returns `VerifiedReviewOutput`

______________________________________________________________________

## Configuration

```bash
# Use a different model for verification (optional)
VERIFY_MODEL_NAME=claude-sonnet-4-20250514

# Default: uses MODEL_NAME from primary review
```

______________________________________________________________________

## Output Format

With `--verify`, each issue includes additional fields:

```markdown
### Issue 1: Null pointer dereference

**Severity:** 🟠 HIGH
**Category:** LOGIC
**Location:** `src/main.py:42`
**Confidence:** 8/10 - Variable is not checked for null in any code path

**Explanation:** ...

**Suggested Fix:** ...
```

______________________________________________________________________

## Limitations

- Adds 3 additional LLM calls per review
- Increases token usage and latency
- Verification quality depends on code context availability
- Low confidence doesn't guarantee false positive (and vice versa)

______________________________________________________________________

## References

- [Chain-of-Verification (CoVe) Paper](https://arxiv.org/abs/2309.11495)
- [Chain of Verification Tutorial](https://learnprompting.org/docs/advanced/self_criticism/chain_of_verification)
