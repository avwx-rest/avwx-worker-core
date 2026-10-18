"""Shared runtime for AVWX background workers.

Everything a worker repo would otherwise copy: environment settings, structured logging,
Sentry reporting, bounded retry, the MongoDB connection, transactional mail, and the shell
a worker runs inside. Deliberately free of any cloud SDK, so the same worker runs under an
Azure Functions timer, a Container Apps job, or a local shell.
"""

from avwx_worker_core.__about__ import __version__
from avwx_worker_core.settings import CoreSettings
from avwx_worker_core.shell import WorkerShell

__all__ = ["CoreSettings", "WorkerShell", "__version__"]
