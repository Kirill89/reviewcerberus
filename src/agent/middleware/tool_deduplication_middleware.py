"""Middleware to prevent duplicate tool calls within a sliding window."""

from collections import deque
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime
from langgraph.typing import ContextT, StateT

from ..prompts import get_prompt


class ToolDeduplicationMiddleware(AgentMiddleware):
    """Prevents agents from making the same tool call repeatedly.

    Tracks recent tool calls in a sliding window and blocks exact duplicates,
    forcing the agent to analyze previous results instead of re-reading.
    """

    def __init__(self, window_size: int = 10) -> None:
        """Initialize the middleware.

        Args:
            window_size: Number of recent tool calls to track for deduplication
        """
        super().__init__()
        self.window_size = window_size
        # Track recent tool calls: (tool_name, args_signature)
        self.recent_calls: deque[tuple[str, str]] = deque(maxlen=window_size)

    def _tool_call_signature(self, tool_call: Any) -> tuple[str, str]:
        """Create a signature for a tool call.

        Args:
            tool_call: Tool call object with 'name' and 'args' attributes or dict

        Returns:
            Tuple of (tool_name, sorted_args_str) for comparison
        """
        # Handle both dict and object formats
        if isinstance(tool_call, dict):
            tool_name = tool_call.get("name", "")
            args = tool_call.get("args", {})
        else:
            tool_name = getattr(tool_call, "name", "")
            args = getattr(tool_call, "args", {})

        # Create stable string representation of args
        # Sort keys to ensure consistent comparison
        args_items = sorted(args.items())
        args_str = str(args_items)

        return (tool_name, args_str)

    def before_model(
        self, state: StateT, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        """Check if the agent is about to make a duplicate tool call.

        This runs after the model has decided to call tools but before they execute.
        """
        messages = state["messages"]  # type: ignore[index]

        # Look for the latest AI message with tool calls
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.tool_calls:
                # Check each tool call for duplicates
                for tool_call in msg.tool_calls:
                    signature = self._tool_call_signature(tool_call)

                    if signature in self.recent_calls:
                        tool_name = signature[0]
                        # Found a duplicate! Inject a warning message
                        agent_name = getattr(runtime.context, "agent_name", "agent")
                        print(
                            f"⚠️  [{agent_name}] Blocked duplicate tool call: {tool_name}"
                        )

                        # Remove the tool call from the message and inject warning
                        warning = get_prompt("tool_deduplication_warning")
                        warning = warning.format(
                            tool_name=tool_name, budget_estimate=self.window_size * 2
                        )
                        return {"messages": [HumanMessage(content=warning)]}

                # If no duplicates found, track these calls for future checks
                for tool_call in msg.tool_calls:
                    signature = self._tool_call_signature(tool_call)
                    self.recent_calls.append(signature)

                break

        return None

    def after_model(
        self, state: StateT, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        """No-op after model execution."""
        return None
