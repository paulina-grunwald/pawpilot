"""Unit tests for the EmailSender protocol and its two stub implementations.

The protocol must stay stable so a real provider (Resend / Postmark / SES)
can be wired in by a single DI swap in a follow-up spec.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

import pytest


def test_email_sender_is_a_protocol_with_send_password_reset() -> None:
    from app.email.sender import EmailSender

    assert isinstance(EmailSender, type(Protocol))
    assert hasattr(EmailSender, "send_password_reset")


async def test_console_email_sender_logs_email_and_url(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from app.email.sender import ConsoleEmailSender

    sender = ConsoleEmailSender()
    reset_url = "http://localhost:3000/reset-password?token=abc.def.ghi"

    with caplog.at_level(logging.INFO):
        await sender.send_password_reset("user@example.com", reset_url)

    combined = " ".join(record.getMessage() for record in caplog.records)
    assert "user@example.com" in combined
    assert reset_url in combined


async def test_in_memory_email_sender_captures_calls() -> None:
    from app.email.sender import InMemoryEmailSender

    sender = InMemoryEmailSender()
    assert sender.calls == []

    await sender.send_password_reset("a@example.com", "http://example/url-a")
    await sender.send_password_reset("b@example.com", "http://example/url-b")

    assert sender.calls == [
        ("a@example.com", "http://example/url-a"),
        ("b@example.com", "http://example/url-b"),
    ]


async def test_in_memory_email_sender_clear() -> None:
    from app.email.sender import InMemoryEmailSender

    sender = InMemoryEmailSender()
    await sender.send_password_reset("x@example.com", "http://example/x")
    assert sender.calls

    sender.clear()
    assert sender.calls == []


def test_implementations_satisfy_protocol() -> None:
    """Structural typing — both stubs are usable wherever EmailSender is expected."""
    from app.email.sender import ConsoleEmailSender, EmailSender, InMemoryEmailSender

    # If EmailSender was declared `@runtime_checkable`, this works directly.
    # Otherwise we fall back to checking the attribute is callable.
    if isinstance(EmailSender, type) and getattr(EmailSender, "_is_runtime_protocol", False):
        protocol: type = EmailSender
        assert isinstance(ConsoleEmailSender(), protocol)
        assert isinstance(InMemoryEmailSender(), protocol)
    else:
        assert callable(getattr(ConsoleEmailSender, "send_password_reset", None))
        assert callable(getattr(InMemoryEmailSender, "send_password_reset", None))


# Keep the import linted-as-used even when the runtime branch above doesn't fire.
_ = runtime_checkable
