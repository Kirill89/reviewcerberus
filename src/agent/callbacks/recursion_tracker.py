"""Callback and middleware for tracking recursion depth and warning agents."""

from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime
from langgraph.typing import ContextT, StateT

from ..prompts import get_prompt


class RecursionTracker(BaseCallbackHandler, AgentMiddleware):
    """Tracks actual recursion depth via callbacks and injects warnings via middleware.

    Unlike the old middleware which estimated steps from message count,
    this uses LangChain callbacks to accurately count chain starts.
    """

    RECURSION_BUDGET_WARNING_MARKER = "__RECURSION_BUDGET_WARNING_"

    def __init__(self, recursion_limit: int, agent_name: str = "agent"):
        """Initialize the tracker.

        Args:
            recursion_limit: Maximum number of recursion steps allowed
            agent_name: Name of the agent for logging
        """
        BaseCallbackHandler.__init__(self)
        AgentMiddleware.__init__(self)
        self.recursion_limit = recursion_limit
        self.agent_name = agent_name
        self.step_count = 0
        self.llm_calls = 0
        self.tool_calls = 0
        self.warned_at: set[float] = set()  # Track which thresholds we've warned at
        self.thresholds = [0.5, 0.7, 0.85]  # 50%, 70%, 85%

    # ========== Callback Methods (for accurate counting) ==========

    def on_chain_start(
        self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any
    ) -> None:
        """Track each chain/graph step."""
        self.step_count += 1

    def on_llm_start(
        self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        """Track LLM calls."""
        self.llm_calls += 1

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Track tool calls."""
        self.tool_calls += 1

    # ========== Middleware Methods (for injecting warnings) ==========

    def _has_warned_at_threshold(self, messages: list[Any], threshold: float) -> bool:
        """Check if we've already warned at this threshold."""
        marker = f"{self.RECURSION_BUDGET_WARNING_MARKER}_{int(threshold * 100)}"
        return any(
            hasattr(msg, "content") and marker in str(msg.content) for msg in messages
        )

    def before_model(
        self, state: StateT, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        """Check recursion depth and inject warning if threshold reached."""
        messages = state["messages"]  # type: ignore[index]

        # Check each threshold and send warning if reached and not already sent
        for threshold in self.thresholds:
            threshold_step = int(self.recursion_limit * threshold)

            if (
                self.step_count >= threshold_step
                and self.step_count < self.recursion_limit
                and not self._has_warned_at_threshold(messages, threshold)
            ):
                remaining = self.recursion_limit - self.step_count
                percentage_used = int((self.step_count / self.recursion_limit) * 100)

                print(
                    f"⚠️  [{self.agent_name}] Recursion budget warning: {percentage_used}% used ({self.step_count}/{self.recursion_limit} steps, {remaining} remaining)"
                )

                marker = (
                    f"{self.RECURSION_BUDGET_WARNING_MARKER}_{int(threshold * 100)}"
                )
                warning = get_prompt("recursion_budget_warning")
                warning = warning.format(
                    percentage_used=percentage_used,
                    current_step=self.step_count,
                    recursion_limit=self.recursion_limit,
                    remaining=remaining,
                )
                # Add marker to the warning so we can detect it later
                warning = f"{warning}\n\n<!-- {marker} -->"

                return {"messages": [HumanMessage(content=warning)]}

        return None

    def after_model(
        self, state: StateT, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        """No-op after model execution."""
        return None

    # ========== Utility Methods ==========

    def get_stats(self) -> dict[str, int]:
        """Get current statistics."""
        return {
            "steps": self.step_count,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "recursion_limit": self.recursion_limit,
            "remaining": self.recursion_limit - self.step_count,
        }
