**CRITICAL: CONTEXT COMPACTION CHECKPOINT**

You are approaching token limits. You MUST create a comprehensive summary NOW
before continuing.

**IMPORTANT:** After this summary, the conversation history will be compacted.
You will ONLY have access to:

1. Your original instruction: "Please review the code changes"
2. THIS SUMMARY

Everything else (tool outputs, diffs, previous reasoning) will be removed.
Therefore, this summary must contain ALL information needed to complete the
review.

**YOUR SUMMARY MUST INCLUDE:**

## Files Examined

List every file you analyzed (with changed_files, diff_file, read_file_part,
search_in_files):

- File path
- What parts you examined (full diff / specific functions / line ranges)
- Why you examined it

## Issues Found (for final report)

Document ALL issues discovered, grouped by severity:

**CRITICAL:**

- [file:line] Brief description and impact

**HIGH:**

- [file:line] Brief description and impact

**MEDIUM:**

- [file:line] Brief description and impact

**LOW:**

- [file:line] Brief description and impact

**POSITIVE OBSERVATIONS:**

- What was done well

## Files NOT Yet Analyzed

List files from changed_files that you haven't examined yet.

## Investigation in Progress

If you're tracing a specific problem or investigating cross-file concerns,
document:

- What you're investigating
- What you've learned so far
- Where to continue

## Next Steps

What should you analyze next and why?

**FORMAT:** Use markdown headings and bullet points. Be specific with file:line
references.

**REMEMBER:** This summary is your ONLY reference after compaction. Include
everything needed to avoid re-analyzing files and to complete the review
successfully.
