# -*- coding: utf-8 -*-
"""
OSC backend which displays notifications through the terminal emulator

The backend asks the terminal emulator to show a notification by writing an OSC
escape sequence to the controlling terminal. It is used as a fallback when no native
notification service is available, for instance on macOS when the process does not run
from an app bundle. Only a title and a message are supported; buttons, reply fields,
sounds, attachments and interaction callbacks are unavailable.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from typing import IO, Mapping

from ..common import Capability, Icon, Notification
from .base import DesktopNotifierBackend

__all__ = [
    "OSCNotificationCenter",
    "detect_protocol",
    "format_notification",
    "is_available",
]

logger = logging.getLogger(__name__)

_STRING_TERMINATOR = "\x1b\\"

# Terminal emulators which display notifications sent via OSC escape sequences. The
# hints are matched against TERM_PROGRAM and TERM, both provided by the terminal.
_TERMINALS_OSC9 = ("iterm", "kitty")
_TERMINALS_OSC777 = ("ghostty", "wezterm", "warp")

_ANSI_RE = re.compile(
    r"\x1b(?:\[[0-?]*[ -/]*[@-~]|][^\x1b\x07]*(?:\x07|\x1b\\)|[@-Z\\-_])"
)
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def detect_protocol(env: Mapping[str, str] | None = None) -> str | None:
    """
    Detect which OSC notification protocol the current terminal supports.

    :param env: Environment to read. Defaults to ``os.environ``.
    :returns: "osc9", "osc777", or None if the terminal does not support either.
    """
    if env is None:
        env = os.environ

    # Notifications from multiplexers would need to be wrapped in a device control
    # string to reach the terminal emulator. This is not implemented.
    if env.get("TMUX") or env.get("STY"):
        return None

    identity = " ".join(filter(None, (env.get("TERM_PROGRAM"), env.get("TERM"))))
    identity = identity.lower()

    for hints, protocol in (
        (_TERMINALS_OSC777, "osc777"),
        (_TERMINALS_OSC9, "osc9"),
    ):
        if any(hint in identity for hint in hints):
            return protocol

    return None


def format_notification(protocol: str, title: str, message: str) -> str:
    """
    Format a notification as an OSC escape sequence.

    :param protocol: Protocol as returned by :func:`detect_protocol`.
    :param title: Notification title.
    :param message: Notification message.
    :raises ValueError: For unknown protocols.
    """
    title = _sanitize(title)
    message = _sanitize(message)

    if protocol == "osc9":
        text = f"{title}: {message}" if title else message
        return f"\x1b]9;{text}{_STRING_TERMINATOR}"

    if protocol == "osc777":
        return f"\x1b]777;notify;{title};{message}{_STRING_TERMINATOR}"

    raise ValueError(f"Unknown protocol: {protocol}")


def is_available(env: Mapping[str, str] | None = None) -> bool:
    """
    Check whether notifications can be displayed by the current terminal.

    :param env: Environment to read. Defaults to ``os.environ``.
    """
    return detect_protocol(env) is not None and _has_terminal()


def _sanitize(text: str) -> str:
    """Remove escape sequences, control characters and superfluous whitespace."""
    text = _ANSI_RE.sub("", text)
    text = " ".join(text.split())
    return _CONTROL_RE.sub("", text)


def _has_terminal() -> bool:
    """Check whether we can write to the controlling terminal."""
    try:
        with open("/dev/tty", "wb", buffering=0):
            return True
    except OSError:
        pass

    for stdio in (sys.stdout, sys.stderr):
        if stdio is not None:
            try:
                if stdio.isatty():
                    return True
            except ValueError:
                continue

    return False


def _write(sequence: str) -> bool:
    """Write an escape sequence to the controlling terminal."""
    data = sequence.encode("utf-8")

    try:
        with open("/dev/tty", "wb", buffering=0) as tty:
            tty.write(data)
            return True
    except OSError:
        pass

    for stdio in (sys.stdout, sys.stderr):
        if stdio is not None:
            try:
                if stdio.isatty():
                    stream: IO[bytes] | None = getattr(stdio, "buffer", None)
                    if stream is not None:
                        stream.write(data)
                        stream.flush()
                        return True
            except (OSError, ValueError):
                continue

    return False


class OSCNotificationCenter(DesktopNotifierBackend):
    """Backend which displays notifications through the terminal emulator

    Notifications are delivered by writing OSC 9 or OSC 777 escape sequences to the
    controlling terminal, which asks the terminal emulator to display them. Only a
    title and a message are supported. The protocol is detected from the terminal's
    environment, see :func:`detect_protocol`.

    :param app_name: The name of the app. Currently unused but kept for interface
        compatibility.
    """

    def __init__(self, app_name: str, app_icon: Icon | None = None) -> None:
        super().__init__(app_name, app_icon)
        self.protocol = detect_protocol()

    async def request_authorisation(self) -> bool:
        """Terminal notifications do not require authorisation."""
        return True

    async def has_authorisation(self) -> bool:
        """Terminal notifications do not require authorisation."""
        return True

    async def _send(self, notification: Notification) -> None:
        protocol = self.protocol or detect_protocol()

        if protocol is None:
            raise RuntimeError("No supported terminal detected")

        sequence = format_notification(
            protocol, notification.title, notification.message
        )
        logger.debug("Sending terminal notification: %s", sequence)

        if not _write(sequence):
            raise OSError("Could not write notification to the terminal")

    async def _clear(self, identifier: str) -> None:
        """Terminal notifications cannot be cleared."""
        pass

    async def _clear_all(self) -> None:
        """Terminal notifications cannot be cleared."""
        pass

    async def _get_capabilities(self) -> frozenset[Capability]:
        return frozenset({Capability.TITLE, Capability.MESSAGE})
