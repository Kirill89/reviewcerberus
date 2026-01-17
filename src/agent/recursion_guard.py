from typing import Any

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.runtime import Runtime

from ..config import TOOL_CALL_LIMIT
from .prompts import get_prompt
from .schema import Context


class ToolCallLimitExceeded(Exception):
    """Raised when the agent exceeds the tool call limit."""


class RecursionGuard(AgentMiddleware[AgentState[Any], Context]):
    """Middleware that forces final output when approaching tool call limit.

    Counts ToolMessage instances in the message history. When the count reaches
    TOOL_CALL_LIMIT, injects a warning message. If the model continues making
    tool calls after the warning, raises ToolCallLimitExceeded.
    """

    def __init__(self) -> None:
        super().__init__()
        self.warned_at_count: int | None = None

    def before_model(
        self, state: AgentState[Any], runtime: Runtime[Context]
    ) -> dict[str, Any] | None:
        """Inject warning or raise exception based on tool call count."""
        tool_count = sum(1 for m in state["messages"] if isinstance(m, ToolMessage))

        # Already warned and model made more tool calls → hard stop
        if self.warned_at_count is not None and tool_count > self.warned_at_count:
            raise ToolCallLimitExceeded(
                f"Agent exceeded tool call limit ({TOOL_CALL_LIMIT}). "
                f"Made {tool_count} tool calls after being warned."
            )

        # Reached limit → inject warning, remember count
        if tool_count >= TOOL_CALL_LIMIT and self.warned_at_count is None:
            print("⚠️  Approaching tool call limit - forcing final output")
            self.warned_at_count = tool_count
            return {
                "messages": [
                    HumanMessage(content=get_prompt("last_step")),
                ],
            }

        return None
