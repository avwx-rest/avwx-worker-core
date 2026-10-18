"""Bounded retry with exponential backoff.

The caller names which exceptions are worth a second attempt: retrying the wrong error
class turns a permanent failure into a slow permanent failure.
"""

from __future__ import annotations

from asyncio import sleep
from typing import TYPE_CHECKING, Final

from avwx_worker_core.observability.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

log = get_logger("retry")

# `sleep` is imported by name so a test can replace `avwx_worker_core.resilience.retry.sleep`
# without touching `asyncio.sleep` itself, which every other coroutine in the process —
# pymongo's connection pool included — also depends on.

DEFAULT_ATTEMPTS: Final = 5
DEFAULT_BASE_DELAY: Final = 0.5


async def with_retry[T](
    operation: Callable[[], Awaitable[T]],
    *,
    description: str,
    errors: tuple[type[BaseException], ...],
    attempts: int = DEFAULT_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
) -> T:
    """Run an operation, retrying the listed exceptions with exponential backoff.

    Raises:
        Exception: whatever the operation raised, once the attempts are exhausted or if
            the exception is not one of `errors`.
    """
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except errors as exc:
            if attempt == attempts:
                log.exception("%s failed after %d attempts", description, attempts)
                raise
            delay = base_delay * 2 ** (attempt - 1)
            log.warning("%s: %s, retrying in %.1fs", description, type(exc).__name__, delay)
            await sleep(delay)
    msg = f"{description} exhausted retries without raising"  # pragma: no cover
    raise RuntimeError(msg)  # pragma: no cover
