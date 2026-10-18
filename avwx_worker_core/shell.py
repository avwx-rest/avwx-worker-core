"""The shell every worker runs inside.

`WorkerShell.run` is what an Azure Functions timer binding, a Container Apps job, and a
local CLI all call. It owns the cross-cutting parts of a run — logging, error reporting,
timing — so a worker is just a coroutine.
"""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING

from avwx_worker_core.observability.errors import configure_error_reporting, report_exception
from avwx_worker_core.observability.logging import configure_logging, get_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable

    from avwx_worker_core.settings import CoreSettings

log = get_logger("shell")


class WorkerShell:
    """Runs workers for one package with its settings and release name."""

    def __init__(self, settings: CoreSettings, *, release: str, namespaces: Iterable[str] = ()) -> None:
        self.settings = settings
        self.release = release
        self.namespaces = tuple(namespaces)

    def configure(self) -> None:
        """Set up logging and error reporting. Idempotent; `run` calls it every time."""
        configure_logging(self.settings, self.namespaces)
        configure_error_reporting(self.settings, release=self.release)

    async def run[R](self, name: str, work: Callable[[], Awaitable[R]]) -> R:
        """Run one worker, logging its result and duration.

        Exceptions are reported and re-raised: a run that dies should fail its invocation
        loudly rather than return a result that looks like there was nothing to do.
        """
        self.configure()
        started = perf_counter()
        log.info("Starting worker %s", name)
        try:
            result = await work()
        except Exception as exc:
            report_exception(exc, worker=name)
            log.exception("Worker %s failed after %.1fs", name, perf_counter() - started)
            raise
        log.info("Finished %s in %.1fs: %s", name, perf_counter() - started, result)
        return result
