"""Outbound transactional email, via Postmark.

Postmark because it refuses to carry marketing mail, so the shared IP pools it uses hold
only transactional senders — what a billing warning or an invoice needs to reach an inbox.

No SDK: the send API is one POST with a token header, and an HTTP client is already a
dependency.

**Sending is off by default.** With `EMAIL_ENABLED=false`, or no server token, the message is
logged instead, which lets every worker that mails run end to end with no provider.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import httpx2
from pydantic_settings import BaseSettings, SettingsConfigDict

from avwx_worker_core.observability.logging import get_logger

if TYPE_CHECKING:
    from avwx_worker_core.mail.message import Message

log = get_logger("mail")

POSTMARK_URL: Final = "https://api.postmarkapp.com/email"
#: A mail provider is never what a worker exists to talk to, so a slow one must not hold a
#: run open.
TIMEOUT_SECONDS: Final = 10.0
#: Postmark returns its own reason in the body; enough of it to diagnose, not a whole page.
_ERROR_BODY_LIMIT: Final = 500


class EmailError(RuntimeError):
    """A send was attempted and did not succeed."""


class PostmarkSettings(BaseSettings):
    """Postmark configuration, read from the same variables shortimer uses."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    email_enabled: bool = False
    postmark_server_token: str = ""
    email_from: str = "AVWX <noreply@avwx.rest>"
    #: Postmark rejects a send whose stream does not exist; "outbound" is the default
    #: transactional stream every server starts with.
    postmark_message_stream: str = "outbound"

    @property
    def active(self) -> bool:
        """Whether messages are actually sent rather than logged."""
        return self.email_enabled and bool(self.postmark_server_token)


class PostmarkMailer:
    """A `Mailer` that sends through Postmark's single-message endpoint."""

    def __init__(
        self, settings: PostmarkSettings, *, transport: httpx2.AsyncBaseTransport | None = None
    ) -> None:
        self.settings = settings
        # Injectable so tests can answer with `httpx2.MockTransport` instead of the network.
        self._transport = transport

    async def send(self, message: Message) -> None:
        """Deliver a message, or log it when sending is switched off.

        Raises:
            EmailError: when a send was attempted and failed, so a caller can tell "could not
                reach them" apart from "chose not to try".
        """
        if not self.settings.active:
            log.info(
                "Email is disabled; not sending %r to %s. Body:\n%s",
                message.subject,
                message.to,
                message.text,
            )
            return

        payload = {
            "From": self.settings.email_from,
            "To": message.to,
            "Subject": message.subject,
            "TextBody": message.text,
            "MessageStream": self.settings.postmark_message_stream,
        }
        if message.cc:
            payload["Cc"] = ", ".join(message.cc)

        try:
            async with httpx2.AsyncClient(timeout=TIMEOUT_SECONDS, transport=self._transport) as client:
                response = await client.post(
                    POSTMARK_URL,
                    json=payload,
                    headers={
                        "X-Postmark-Server-Token": self.settings.postmark_server_token,
                        "Accept": "application/json",
                    },
                )
        except httpx2.HTTPError as exc:
            msg = f"Could not reach Postmark: {exc}"
            raise EmailError(msg) from exc

        if response.status_code != httpx2.codes.OK:
            log.error(
                "Postmark rejected a send to %s: %s %s",
                message.to,
                response.status_code,
                response.text[:_ERROR_BODY_LIMIT],
            )
            msg = f"Postmark rejected the message with HTTP {response.status_code}"
            raise EmailError(msg)
        log.info("Sent %r to %s", message.subject, message.to)
