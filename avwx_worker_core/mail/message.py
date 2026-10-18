"""The message shape and the interface a mail transport implements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Message:
    """A plain-text email ready to hand to a `Mailer`."""

    to: str
    subject: str
    text: str
    cc: tuple[str, ...] = ()


class Mailer(Protocol):
    """Anything that can deliver a `Message`.

    Workers depend on this rather than on Postmark, so a test can capture what would have
    been sent and a provider change touches one class.
    """

    async def send(self, message: Message) -> None:
        """Deliver a message, raising `EmailError` when an attempted send fails."""
        ...
