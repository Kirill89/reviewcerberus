"""Token usage tracking dataclass."""

from dataclasses import dataclass
from typing import Any


@dataclass
class TokenUsage:
    """Tracks token usage for LLM calls.

    Attributes:
        input_tokens: Total input tokens used
        output_tokens: Total output tokens used
        total_tokens: Total tokens (input + output)
    """

    input_tokens: int
    output_tokens: int
    total_tokens: int

    @staticmethod
    def from_response(response: dict[str, Any]) -> "TokenUsage | None":
        """Extract token usage from agent response.

        Args:
            response: Agent response containing messages with usage_metadata

        Returns:
            TokenUsage instance or None if no usage data found
        """
        total_output = 0
        cumulative_total = 0

        if "messages" in response:
            for msg in response["messages"]:
                if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                    usage = msg.usage_metadata
                    total_output += usage.get("output_tokens", 0)
                    cumulative_total = usage.get("total_tokens", 0)

        if cumulative_total > 0:
            total_input = cumulative_total - total_output
            return TokenUsage(
                input_tokens=total_input,
                output_tokens=total_output,
                total_tokens=cumulative_total,
            )

        return None

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Add two TokenUsage instances together.

        Args:
            other: Another TokenUsage instance

        Returns:
            New TokenUsage with summed values
        """
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )

    def print(self) -> None:
        """Print token usage in a formatted way."""
        print(f"Token Usage:")
        print(f"  Input tokens:  {self.input_tokens:>7,}")
        print(f"  Output tokens: {self.output_tokens:>7,}")
        print(f"  Total tokens:  {self.total_tokens:>7,}")
