"""Structured logging shared by every worker."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Final

from pythonjsonlogger.json import JsonFormatter

if TYPE_CHECKING:
    from collections.abc import Iterable

    from avwx_worker_core.settings import CoreSettings

PLAIN_FORMAT: Final = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
JSON_FORMAT: Final = "%(asctime)s %(name)s %(levelname)s %(message)s"
CORE_NAMESPACE: Final = "avwx_worker_core"


def configure_logging(settings: CoreSettings, namespaces: Iterable[str] = ()) -> None:
    """Attach a single stdout handler to each package logger named.

    The core's own logger is always included. Safe to call more than once: a second call
    replaces the handler rather than stacking another, which is what produces duplicate
    lines under Azure Functions, where the host reuses a process across invocations.
    """
    formatter = logging.Formatter(PLAIN_FORMAT) if settings.log_plain else JsonFormatter(JSON_FORMAT)
    for namespace in dict.fromkeys((CORE_NAMESPACE, *namespaces)):
        logger = logging.getLogger(namespace)
        logger.setLevel(settings.log_level.upper())
        logger.propagate = False
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        for existing in list(logger.handlers):
            logger.removeHandler(existing)
        logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """A logger under the core's namespace, for the core's own modules."""
    return logging.getLogger(f"{CORE_NAMESPACE}.{name}")
