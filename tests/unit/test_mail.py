"""Postmark delivery."""

from __future__ import annotations

import json

import httpx2
import pytest

from avwx_worker_core.mail import EmailError, Message, PostmarkMailer, PostmarkSettings

pytestmark = pytest.mark.unit

MESSAGE = Message(to="pilot@example.com", subject="Hello", text="Body", cc=("copy@example.com",))


def settings(*, enabled: bool = True, token: str = "server-token") -> PostmarkSettings:
    return PostmarkSettings(email_enabled=enabled, postmark_server_token=token, email_from="AVWX <a@b.c>")


async def test_sends_through_postmark() -> None:
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json={"ErrorCode": 0})

    await PostmarkMailer(settings(), transport=httpx2.MockTransport(handler)).send(MESSAGE)

    (request,) = seen
    assert request.headers["X-Postmark-Server-Token"] == "server-token"
    body = json.loads(request.content)
    assert body == {
        "From": "AVWX <a@b.c>",
        "To": "pilot@example.com",
        "Subject": "Hello",
        "TextBody": "Body",
        "MessageStream": "outbound",
        "Cc": "copy@example.com",
    }


@pytest.mark.parametrize(("enabled", "token"), [(False, "server-token"), (True, "")])
async def test_disabled_sends_nothing(enabled: bool, token: str) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        pytest.fail("no request should be made")

    mailer = PostmarkMailer(settings(enabled=enabled, token=token), transport=httpx2.MockTransport(handler))
    await mailer.send(MESSAGE)


async def test_rejection_raises() -> None:
    transport = httpx2.MockTransport(lambda _: httpx2.Response(422, json={"ErrorCode": 300}))
    with pytest.raises(EmailError, match="422"):
        await PostmarkMailer(settings(), transport=transport).send(MESSAGE)


async def test_unreachable_raises() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("down", request=request)

    with pytest.raises(EmailError, match="Could not reach"):
        await PostmarkMailer(settings(), transport=httpx2.MockTransport(handler)).send(MESSAGE)
