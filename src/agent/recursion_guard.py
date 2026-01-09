from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime
from langgraph.typing import ContextT, StateT

from ..config import RECURSION_LIMIT
from .prompts import get_prompt

# Reserve steps for the model to generate final structured output
STEPS_BUFFER = 4


class RecursionGuard(AgentMiddleware, BaseCallbackHandler):
    """Middleware and callback that forces final output before hitting recursion limit.

    This class serves dual purposes:
    1. As a BaseCallbackHandler: tracks graph steps via on_chain_start
    2. As an AgentMiddleware: injects a message forcing output when approaching limit

    The same instance must be passed to both the agent middleware list and
    the invoke config callbacks list.
    """

    def __init__(self) -> None:
        AgentMiddleware.__init__(self)
        BaseCallbackHandler.__init__(self)
        self.step_count = 0

    def on_chain_start(
        self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any
    ) -> None:
        """Track each graph step execution."""
        self.step_count += 1

    def before_model(
        self, state: StateT, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        """Inject message to force final output when approaching recursion limit."""
        steps_remaining = RECURSION_LIMIT - self.step_count

        if steps_remaining <= STEPS_BUFFER:
            print("⚠️  Approaching recursion limit - forcing final output")

            return {
                "messages": [
                    HumanMessage(content=get_prompt("last_step")),
                ],
            }

        return None
