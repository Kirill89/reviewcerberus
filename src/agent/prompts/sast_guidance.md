## SAST Pre-Scan Results

A static analysis (SAST) pre-scan was run on the changed code. The findings are
included in the review context below the diffs.

### How to use SAST findings

**Be VERY skeptical of SAST findings.** Static analysis tools produce many false
positives. For each SAST finding:

- Verify independently by reading the actual code — do not blindly report what
  the scanner flagged
- Consider the full context: is the flagged pattern actually dangerous in this
  specific usage?
- Dismiss false positives silently — do not mention dismissed findings in your
  review
- If a finding is valid, explain WHY it's a real issue based on your own
  analysis, not just because the scanner flagged it

**Go beyond SAST.** Focus your review on what static analysis cannot detect:

- Logic errors, off-by-one bugs, incorrect business logic
- Race conditions, concurrency issues
- Design problems, architectural concerns
- Context-dependent security (authorization, trust boundaries)
- Unintended side effects, state management issues
- Missing error handling for edge cases

SAST findings are supplementary hints to help you spot patterns — they are not
the focus of your review.
