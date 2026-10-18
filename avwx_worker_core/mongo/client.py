"""The MongoDB client for the duration of one worker run."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from pymongo import AsyncMongoClient

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from avwx_worker_core.settings import CoreSettings


@asynccontextmanager
async def mongo_client(settings: CoreSettings) -> AsyncIterator[AsyncMongoClient[dict[str, Any]]]:
    """Open a timezone-aware client, closed when the run ends.

    A client per run rather than per process: a timer invocation may land on a fresh host,
    and a cached client outliving its event loop fails in ways that look like network faults.
    """
    client: AsyncMongoClient[dict[str, Any]] = AsyncMongoClient(settings.mongo_uri, tz_aware=True)
    try:
        yield client
    finally:
        await client.close()
