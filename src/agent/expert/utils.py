"""Utility functions for multi-agent system."""

import asyncio
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


async def retry_async(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    operation_name: str = "Operation",
    show_progress: bool = True,
) -> T:
    """Retry an async operation with exponential backoff.

    Args:
        func: Async function to retry (should be a callable that returns an awaitable)
        max_retries: Maximum number of retry attempts
        operation_name: Name of the operation for logging
        show_progress: Whether to show progress messages

    Returns:
        Result of the successful function call

    Raises:
        Exception: The last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            if show_progress and attempt > 0:
                print(f"  Retrying {operation_name}... (attempt {attempt + 1})")

            return await func()

        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                if show_progress:
                    print(f"  Warning: {operation_name} failed, retrying... ({str(e)})")
                await asyncio.sleep(2 ** (attempt + 1))  # Exponential backoff
            else:
                if show_progress:
                    print(
                        f"  Error: {operation_name} failed after {max_retries + 1} attempts"
                    )

    # If we got here, all retries failed
    raise Exception(
        f"{operation_name} failed after {max_retries + 1} attempts: {last_exception}"
    )
