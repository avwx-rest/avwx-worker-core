"""Retry policy for MongoDB operations.

Mirrors `mongo_handler` on the API side: transient connection faults are retried with
backoff, while an `OperationFailure` is raised immediately, because retrying it only delays
the same error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from pymongo.errors import ConnectionFailure

from avwx_worker_core.resilience.retry import DEFAULT_ATTEMPTS, DEFAULT_BASE_DELAY, with_retry

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

# `ConnectionFailure` covers `AutoReconnect`, `NetworkTimeout`, and
# `ServerSelectionTimeoutError`. Anything else, `OperationFailure` included, propagates.
TRANSIENT_ERRORS: Final[tuple[type[BaseException], ...]] = (ConnectionFailure,)


async def with_mongo_retry[T](
    operation: Callable[[], Awaitable[T]],
    *,
    description: str,
    attempts: int = DEFAULT_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
) -> T:
    """Run a Mongo operation, retrying transient connection failures."""
    return await with_retry(
        operation,
        description=description,
        errors=TRANSIENT_ERRORS,
        attempts=attempts,
        base_delay=base_delay,
    )
