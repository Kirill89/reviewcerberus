## TOOL USAGE EFFICIENCY

**Read files efficiently:**

- When you need to understand a file, read more data at once (use
  num_lines=1000)
- Avoid making many small reads of the same file - this wastes recursion budget
- Plan what you need upfront rather than reading incrementally

**Use the reasoning parameter:**

- Tools like read_file_part and search_in_files have an optional `reasoning`
  parameter
- Use it to explain what you're looking for: reasoning="Checking for missing
  test coverage"
- This helps track decision-making and improve tool usage patterns

**Why this matters:**

- Each tool call consumes recursion budget
- Reading a 400-line file in 20 small chunks is much slower than one large read
- You have limited recursion budget - use it wisely
