"""Error reporting.

Sentry is the destination, but workers call `report_exception` rather than the SDK, which
keeps the reporter swappable and makes the no-DSN case (local runs, tests) a log line
rather than a silent drop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import sentry_sdk

from avwx_worker_core.observability.logging import get_logger

if TYPE_CHECKING:
    from avwx_worker_core.settings import CoreSettings

log = get_logger("errors")

_enabled = False


def configure_error_reporting(settings: CoreSettings, *, release: str) -> None:
    """Initialize Sentry when a DSN is configured."""
    global _enabled  # noqa: PLW0603 - one process-wide reporter, like the SDK itself
    if not settings.sentry_dsn:
        log.info("Sentry DSN not set; exceptions will only be logged")
        _enabled = False
        return
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, release=release)
    _enabled = True


def report_exception(exc: BaseException, **context: Any) -> None:
    """Report a handled exception without interrupting the run.

    Context is attached as a Sentry "worker" context and included in the log record, so
    whatever identifies the failing item is recoverable either way.
    """
    log.warning("%s: %s", type(exc).__name__, exc, extra=context, exc_info=exc)
    if not _enabled:
        return
    with sentry_sdk.new_scope() as scope:
        scope.set_context("worker", context)
        sentry_sdk.capture_exception(exc)
