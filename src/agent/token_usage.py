"""Token usage tracking utilities."""

from dataclasses import dataclass
from typing import Any


@dataclass
class TokenUsage:
    """Represents token usage for LLM calls."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens used."""
        return self.input_tokens + self.output_tokens

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Add two TokenUsage instances together."""
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )

    def log_statistics(self, prefix: str = "") -> None:
        """Log token usage statistics.

        Args:
            prefix: Optional prefix for the log message (e.g., agent name)
        """
        prefix_str = f"[{prefix}] " if prefix else ""
        print(f"{prefix_str}Token usage:")
        print(f"  Input tokens:  {self.input_tokens:,}")
        print(f"  Output tokens: {self.output_tokens:,}")
        print(f"  Total tokens:  {self.total_tokens:,}")

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary format for compatibility."""
        return {
            "total_input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


def extract_token_usage(obj: Any) -> TokenUsage | None:
    """Extract token usage from an object with usage_metadata.

    Args:
        obj: Object that may have usage_metadata attribute (e.g., AIMessage)

    Returns:
        TokenUsage instance if usage metadata found, None otherwise
    """
    if not hasattr(obj, "usage_metadata") or not obj.usage_metadata:
        return None

    usage = obj.usage_metadata
    return TokenUsage(
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
    )


def aggregate_token_usage(messages: list[Any]) -> TokenUsage:
    """Aggregate token usage from a list of messages.

    This handles the case where cumulative totals increase with each message.
    We sum output tokens and calculate input as: final_cumulative - total_output.

    Args:
        messages: List of messages with usage_metadata

    Returns:
        Aggregated TokenUsage
    """
    total_output = 0
    cumulative_total = 0

    for msg in messages:
        if hasattr(msg, "usage_metadata") and msg.usage_metadata:
            usage = msg.usage_metadata
            # Sum output tokens from each turn
            total_output += usage.get("output_tokens", 0)
            # Keep final cumulative total (increases each turn)
            cumulative_total = usage.get("total_tokens", 0)

    # Calculate total input as: cumulative_total - total_output
    total_input = cumulative_total - total_output

    return TokenUsage(input_tokens=total_input, output_tokens=total_output)
