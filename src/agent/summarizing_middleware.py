from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
)
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.runtime import Runtime
from langgraph.typing import ContextT, StateT

from ..config import CONTEXT_COMPACT_THRESHOLD
from .prompts import get_prompt


class SummarizingMiddleware(AgentMiddleware):
    def __init__(self) -> None:
        super().__init__()
        self.summary_requested = False

    def before_model(
        self, state: StateT, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        messages = state["messages"]  # type: ignore[index]
        total_tokens = count_tokens_approximately(messages)

        if total_tokens > CONTEXT_COMPACT_THRESHOLD:
            print(f"🔄 Context compaction triggered:")
            print(f"   Total tokens: ~{total_tokens:,}")
            print(f"   Injecting summarization request...")

            self.summary_requested = True

            return {
                "messages": [
                    HumanMessage(content=get_prompt("context_summary")),
                ],
            }

        return None

    def after_model(
        self, state: StateT, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        if not self.summary_requested:
            return None

        self.summary_requested = False
        messages = state["messages"]  # type: ignore[index]
        remove_messages = []

        for message in messages[1:]:
            remove_messages.append(RemoveMessage(id=message.id))

        last_message_with_tools = next(
            m
            for m in reversed(messages)
            if isinstance(m, AIMessage) and len(m.tool_calls) > 0
        )

        return {
            "messages": remove_messages
            + [
                AIMessage(
                    content=messages[-1].content,
                    tool_calls=last_message_with_tools.tool_calls,
                ),
            ],
        }
