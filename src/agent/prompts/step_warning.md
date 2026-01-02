⚠️ **EFFICIENCY REMINDER: Step {current_step} of {recursion_limit}**

You have **{remaining_steps} steps remaining**.

**Use them wisely:**

- **BATCH YOUR TOOL CALLS**: Make ~10 parallel tool calls per step instead of
  sequential calls
- **DON'T WASTE TOKENS**: Avoid reading files you've already seen, don't search
  for patterns you already found
- **PRIORITIZE**: Focus on the most important findings first
- **BE EFFICIENT**: Skip redundant validation steps

Every tool call counts as a step. Batch calling 10 tools = 1 step. Sequential
calling 10 tools = 10 steps.
