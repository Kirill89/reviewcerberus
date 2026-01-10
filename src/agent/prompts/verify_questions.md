# Verification Step 1: Generate Falsification Questions

You are verifying code review findings to reduce false positives. For each issue
below, generate **falsification questions** - questions where a "NO" answer
would indicate the issue is a false positive.

## Guidelines

- Generate 1-10 questions per issue depending on complexity
- Questions should be answerable from the provided code context
- Focus on verifying:
  - Whether the issue actually exists in the code
  - Whether the described behavior is accurate
  - Whether the suggested fix addresses a real problem
- Each question should test a specific claim in the issue
- A "NO" answer to any question weakens confidence in the issue

## Example Questions

For an issue about "Missing null check before accessing .profile":

- Does the function access the `.profile` property?
- Is there any existing null/undefined check before accessing `.profile`?
- Can the object being accessed actually be null at this point in the code?

## Original Review Context

{original_system_prompt}

## Code Changes Under Review

{user_message}

## Code Context Read During Review

{file_context}

## Issues to Verify

{issues_with_ids}
