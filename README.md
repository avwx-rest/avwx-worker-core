# avwx-worker-core

Core utilities for AVWX function workers: the parts every worker repo would otherwise copy.

| Module | What it provides |
| --- | --- |
| `avwx_worker_core.settings` | `CoreSettings`, the environment settings every worker shares. Subclass it. |
| `avwx_worker_core.shell` | `WorkerShell`, which runs a worker coroutine with logging, Sentry, and timing |
| `avwx_worker_core.observability` | JSON or plain stdout logging, and `report_exception` for Sentry |
| `avwx_worker_core.resilience` | `with_retry`, bounded exponential backoff over named exceptions |
| `avwx_worker_core.mongo` | A per-run `AsyncMongoClient`, `with_mongo_retry`, and `ObjectIdField` for pydantic |
| `avwx_worker_core.mail` | The `Mailer` interface and `PostmarkMailer` |

Nothing here imports a cloud SDK. A worker built on it runs the same under an Azure
Functions timer, a Container Apps job, or a local shell.

## Using it

Workers install it from a pinned commit's archive. Unlike a git source, a tarball installs in
CI, on the Azure Functions Oryx build, and in a slim container image without git:

```toml
[project]
dependencies = ["avwx-worker-core"]

[tool.uv.sources]
avwx-worker-core = { url = "https://github.com/avwx-rest/avwx-worker-core/archive/<commit>.tar.gz" }
```

A worker repo defines its settings and one shell:

```python
from avwx_worker_core import CoreSettings, WorkerShell

class Settings(CoreSettings):
    account_database: str = "account"

CFG = Settings()
SHELL = WorkerShell(CFG, release="my-workers@1.0.0", namespaces=["my_workers"])

result = await SHELL.run("my-worker", my_worker_coroutine_function)
```

`run` reports and re-raises any exception, so a failed run fails its invocation rather
than looking like an empty one.

## Mail

`PostmarkMailer` reads the same variables shortimer does:

| Variable | Default | |
| --- | --- | --- |
| `EMAIL_ENABLED` | `false` | Off means every message is logged instead of sent |
| `POSTMARK_SERVER_TOKEN` | | Also required to send |
| `EMAIL_FROM` | `AVWX <noreply@avwx.rest>` | |
| `POSTMARK_MESSAGE_STREAM` | `outbound` | Postmark rejects a stream that does not exist |

No SDK: the send API is one POST, and `httpx2` is already a dependency.

## Development

```bash
hatch test -a
```

```bash
hatch run types:check
```

```bash
hatch check code && hatch check fmt
```
