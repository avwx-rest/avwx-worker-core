"""Settings, retry, the worker shell, and Mongo field types."""

from __future__ import annotations

import logging

import pytest
from bson import ObjectId
from pydantic import BaseModel, ValidationError
from pymongo.errors import AutoReconnect, OperationFailure

from avwx_worker_core import CoreSettings, WorkerShell
from avwx_worker_core.mongo import ObjectIdField, with_mongo_retry
from avwx_worker_core.observability import configure_logging, errors
from avwx_worker_core.resilience import retry

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def instant(_: float) -> None:
        return None

    monkeypatch.setattr(retry, "sleep", instant)


def test_database_name_suffix() -> None:
    assert CoreSettings(testing=False).database_name("account") == "account"
    assert CoreSettings(testing=True).database_name("account") == "account-tests"


def test_logging_is_idempotent() -> None:
    settings = CoreSettings(log_plain=True)
    configure_logging(settings, ["some_package"])
    configure_logging(settings, ["some_package"])
    assert len(logging.getLogger("some_package").handlers) == 1
    assert len(logging.getLogger("avwx_worker_core").handlers) == 1


async def test_retry_recovers_from_transient_errors() -> None:
    calls = 0

    async def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise AutoReconnect("blip")
        return "ok"

    assert await with_mongo_retry(flaky, description="flaky") == "ok"
    assert calls == 3


async def test_retry_gives_up() -> None:
    async def down() -> None:
        raise AutoReconnect("down")

    with pytest.raises(AutoReconnect):
        await with_mongo_retry(down, description="down", attempts=2)


async def test_retry_does_not_retry_permanent_errors() -> None:
    calls = 0

    async def broken() -> None:
        nonlocal calls
        calls += 1
        raise OperationFailure("bad index")

    with pytest.raises(OperationFailure):
        await with_mongo_retry(broken, description="broken")
    assert calls == 1


async def test_shell_returns_result() -> None:
    async def work() -> int:
        return 42

    assert await WorkerShell(CoreSettings(), release="t@0").run("answer", work) == 42


async def test_shell_reports_and_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    reported: list[BaseException] = []
    monkeypatch.setattr("avwx_worker_core.shell.report_exception", lambda exc, **_: reported.append(exc))

    async def work() -> None:
        msg = "upstream is down"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="upstream is down"):
        await WorkerShell(CoreSettings(), release="t@0").run("broken", work)
    assert isinstance(reported[0], RuntimeError)


def test_report_without_dsn_only_logs() -> None:
    errors.configure_error_reporting(CoreSettings(sentry_dsn=None), release="t@0")
    errors.report_exception(ValueError("x"), item="abc")


class Doc(BaseModel):
    id: ObjectIdField


def test_object_id_field() -> None:
    oid = ObjectId()
    assert Doc.model_validate({"id": str(oid)}).id == oid
    assert Doc(id=oid).model_dump()["id"] == oid
    assert Doc(id=oid).model_dump(mode="json")["id"] == str(oid)
    with pytest.raises(ValidationError):
        Doc.model_validate({"id": "nope"})
