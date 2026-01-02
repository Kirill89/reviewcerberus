"""Token warning injector that warns the LLM when approaching context window limits.

Tracks token usage and injects warning messages into the conversation when
thresholds are reached. Does not enforce hard limits.
"""

from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime
from langgraph.typing import ContextT, StateT

from ..prompts import get_prompt


class TokenWarningInjector(BaseCallbackHandler, AgentMiddleware):
    """Tracks token usage and warns LLM when approaching context limits.

    Works as both a callback (to track tokens) and middleware (to inject warnings).
    """

    def __init__(self, max_context_window: int = 200000, recursion_limit: int = 200):
        """Initialize token warning injector.

        Args:
            max_context_window: Maximum context window size in tokens. Defaults to 200k.
            recursion_limit: Maximum agent steps (recursion limit). Defaults to 200.
        """
        self.max_context_window = max_context_window
        self.recursion_limit = recursion_limit
        self.total_tokens = 0
        self.step_count = 0

        # Warning thresholds as percentages of max context window
        self.warning_thresholds = [
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.85,
            0.9,
            0.95,
        ]

        # Track which warnings have been sent to avoid duplicates
        self.warnings_sent: set[float] = set()
        self.step_warnings_sent: set[int] = set()

        # Load warning message templates
        self.warning_template = get_prompt("token_warning")
        self.step_warning_template = get_prompt("step_warning")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Callback invoked after each LLM call to track token usage."""
        # Extract usage from the first generation's message
        if response.generations and len(response.generations) > 0:
            generation = response.generations[0][0]
            if hasattr(generation, "message") and hasattr(
                generation.message, "usage_metadata"
            ):
                usage_metadata = generation.message.usage_metadata
                if usage_metadata:
                    # usage_metadata already contains cumulative total, not delta
                    cumulative_tokens = usage_metadata.get("total_tokens", 0)
                    step_tokens = cumulative_tokens - self.total_tokens
                    self.total_tokens = cumulative_tokens

                    # Calculate percentage of context window used
                    percentage = (self.total_tokens / self.max_context_window) * 100

                    print(
                        f"Step tokens: {step_tokens:,} | Running total: {self.total_tokens:,} ({percentage:.1f}%)"
                    )

    def before_model(
        self, state: StateT, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        """Middleware invoked before each model call to inject warnings if needed.

        Args:
            state: Current agent state
            runtime: Runtime context

        Returns:
            Dict with warning message to inject, or None if no warning needed
        """
        # Increment step counter
        self.step_count += 1

        # Check for step warnings (every 10 steps)
        if self.step_count % 10 == 0 and self.step_count not in self.step_warnings_sent:
            self.step_warnings_sent.add(self.step_count)
            remaining_steps = self.recursion_limit - self.step_count

            # Log step warning to console
            print(f"⚠️  Step limit warning:")
            print(
                f"   Current step: {self.step_count} / {self.recursion_limit} (Remaining: {remaining_steps})"
            )
            print(f"   Injecting efficiency reminder to LLM...")

            # Format step warning message
            step_warning_content = self.step_warning_template.format(
                current_step=self.step_count,
                remaining_steps=remaining_steps,
                recursion_limit=self.recursion_limit,
            )

            step_warning = HumanMessage(content=step_warning_content)

            # Inject step warning message
            return {"messages": [step_warning]}

        # Check if we've crossed any token warning thresholds
        for threshold_pct in self.warning_thresholds:
            threshold_tokens = int(self.max_context_window * threshold_pct)

            # If we've crossed this threshold and haven't warned yet
            if (
                self.total_tokens >= threshold_tokens
                and threshold_pct not in self.warnings_sent
            ):
                self.warnings_sent.add(threshold_pct)

                # Log warning to console
                print(f"⚠️  Token usage warning triggered:")
                print(
                    f"   Current: {self.total_tokens:,} / {self.max_context_window:,} tokens ({threshold_pct*100:.0f}%)"
                )
                print(f"   Injecting warning message to LLM...")

                # Format warning message with actual numbers
                warning_content = self.warning_template.format(
                    current_tokens=f"{self.total_tokens:,}",
                    max_tokens=f"{self.max_context_window:,}",
                    percentage=f"{threshold_pct*100:.0f}",
                )

                warning = HumanMessage(content=warning_content)

                # Inject warning message into conversation
                return {"messages": [warning]}

        return None
