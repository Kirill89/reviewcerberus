import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler


class ProgressCallbackHandler(BaseCallbackHandler):
    """Callback handler for displaying agent progress."""

    def __init__(self) -> None:
        super().__init__()
        self._llm_start_time: float | None = None

    def on_llm_start(self, serialized: Any, prompts: Any, **kwargs: Any) -> None:
        """Called when LLM starts generating."""
        self._llm_start_time = time.time()
        print("🤔 Thinking...")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Called when LLM finishes generating."""
        if self._llm_start_time:
            duration = time.time() - self._llm_start_time
            self._llm_start_time = None
            print(f"⏱️ {duration:.1f}s")
