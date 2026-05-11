"""Email sender protocol + stub implementations.

The real provider (Resend / Postmark / SES) lands in a follow-up spec — wiring
it in is a one-line dependency swap because `get_email_sender` is overridable
via FastAPI's `dependency_overrides`.

TODO: replace `ConsoleEmailSender` with a real provider — tracked in a
follow-up spec.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger("app.email")


@runtime_checkable
class EmailSender(Protocol):
    async def send_password_reset(self, email: str, reset_url: str) -> None: ...


class ConsoleEmailSender:
    """Logs the reset URL to stdout — used in dev, never in production."""

    async def send_password_reset(self, email: str, reset_url: str) -> None:
        logger.info("[email:reset] to=%s url=%s", email, reset_url)


class InMemoryEmailSender:
    """Test double — captures every call so tests can assert against it."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def send_password_reset(self, email: str, reset_url: str) -> None:
        self.calls.append((email, reset_url))

    def clear(self) -> None:
        self.calls.clear()


_default_sender: EmailSender = ConsoleEmailSender()


def get_email_sender() -> EmailSender:
    return _default_sender
