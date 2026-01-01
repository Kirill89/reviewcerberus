🚫 CRITICAL ERROR: Duplicate file read detected!

You already accessed lines {lines_str} in {file_path}. This content is ALREADY
in your context from a previous read.

This should NEVER happen. Re-reading the same lines wastes valuable tokens and
degrades performance.

YOU MUST:

- Use the information from your previous read that is already in your context
- Review your conversation history to find the content you already accessed
- NEVER request the same file content twice

Use tokens wisely. Stop wasting resources on duplicate reads.
