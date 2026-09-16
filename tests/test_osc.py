from __future__ import annotations

import io
import sys
from typing import Any
from unittest.mock import patch

import pytest

from desktop_notifier import Capability, Notification
from desktop_notifier.backends import osc
from desktop_notifier.backends.osc import (
    OSCNotificationCenter,
    detect_protocol,
    format_notification,
)

ST = "\x1b\\"


class FakeStdio:
    """Minimal stand-in for sys.stdout / sys.stderr."""

    def __init__(self, tty: bool, buffer: Any = None) -> None:
        self.buffer = buffer
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


class ClosedStdio(FakeStdio):
    """Stand-in whose isatty call raises like a closed stream."""

    def isatty(self) -> bool:
        raise ValueError("I/O operation on closed file")


class BrokenBuffer:
    """Stand-in buffer whose writes fail."""

    def write(self, data: bytes) -> int:
        raise OSError("Broken pipe")

    def flush(self) -> None:
        pass


class RecordingStream:
    """Binary stream which stays readable after leaving a context manager."""

    def __init__(self) -> None:
        self.data = b""

    def write(self, data: bytes) -> int:
        self.data += data
        return len(data)

    def flush(self) -> None:
        pass

    def __enter__(self) -> RecordingStream:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        pass


@pytest.mark.parametrize(
    "env,expected",
    [
        ({"TERM_PROGRAM": "ghostty", "TERM": "xterm-ghostty"}, "osc777"),
        ({"TERM_PROGRAM": "WezTerm"}, "osc777"),
        ({"TERM_PROGRAM": "WarpTerminal"}, "osc777"),
        ({"TERM_PROGRAM": "iTerm.app"}, "osc9"),
        ({"TERM_PROGRAM": "kitty"}, "osc9"),
        ({"TERM": "xterm-kitty"}, "osc9"),
        ({"TERM_PROGRAM": "Apple_Terminal"}, None),
        ({"TERM_PROGRAM": "vscode"}, None),
        ({"TERM": "dumb"}, None),
        ({}, None),
        # Notifications from multiplexers would need DCS passthrough.
        ({"TERM_PROGRAM": "ghostty", "TMUX": "/tmp/tmux-501/default,1,0"}, None),
        ({"TERM_PROGRAM": "ghostty", "STY": "1234.pts-0.host"}, None),
    ],
)
def test_detect_protocol(env: dict[str, str], expected: str | None) -> None:
    assert detect_protocol(env) == expected


def test_format_notification() -> None:
    assert (
        format_notification("osc9", "Title", "Message") == "\x1b]9;Title: Message" + ST
    )
    assert format_notification("osc9", "", "Message") == "\x1b]9;Message" + ST
    assert (
        format_notification("osc777", "Title", "Message")
        == "\x1b]777;notify;Title;Message" + ST
    )


def test_format_notification_sanitizes_text() -> None:
    assert (
        format_notification("osc777", "Ti\ntle", "\x1b[31mred\x1b[0m")
        == "\x1b]777;notify;Ti tle;red" + ST
    )


def test_format_notification_rejects_unknown_protocol() -> None:
    with pytest.raises(ValueError):
        format_notification("osc99", "Title", "Message")


@pytest.mark.asyncio
async def test_send_writes_escape_sequence(monkeypatch: pytest.MonkeyPatch) -> None:
    written: list[str] = []

    def fake_write(sequence: str) -> bool:
        written.append(sequence)
        return True

    monkeypatch.setattr(osc, "_write", fake_write)

    backend = OSCNotificationCenter("Test")
    backend.protocol = "osc9"
    await backend.send(Notification(title="Title", message="Message"))

    assert written == ["\x1b]9;Title: Message" + ST]
    assert len(await backend.get_current_notifications()) == 1


def test_detect_protocol_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERM_PROGRAM", "ghostty")
    monkeypatch.delenv("TERM", raising=False)
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("STY", raising=False)
    assert detect_protocol() == "osc777"


def test_is_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(osc, "detect_protocol", lambda env=None: "osc777")
    monkeypatch.setattr(osc, "_has_terminal", lambda: True)
    assert osc.is_available() is True

    monkeypatch.setattr(osc, "_has_terminal", lambda: False)
    assert osc.is_available() is False


def test_has_terminal_with_controlling_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: io.BytesIO())
    assert osc._has_terminal() is True


def test_has_terminal_with_standard_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_open(*args: object, **kwargs: object) -> io.BytesIO:
        raise OSError("No controlling terminal")

    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr(sys, "stdout", FakeStdio(tty=True))
    assert osc._has_terminal() is True


def test_has_terminal_without_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_open(*args: object, **kwargs: object) -> io.BytesIO:
        raise OSError("No controlling terminal")

    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr(sys, "stdout", FakeStdio(tty=False))
    monkeypatch.setattr(sys, "stderr", FakeStdio(tty=False))
    assert osc._has_terminal() is False


def test_has_terminal_ignores_closed_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_open(*args: object, **kwargs: object) -> io.BytesIO:
        raise OSError("No controlling terminal")

    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr(sys, "stdout", ClosedStdio(tty=True))
    monkeypatch.setattr(sys, "stderr", FakeStdio(tty=False))
    assert osc._has_terminal() is False


def test_write_uses_controlling_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    streams: list[RecordingStream] = []

    def fake_open(*args: object, **kwargs: object) -> RecordingStream:
        stream = RecordingStream()
        streams.append(stream)
        return stream

    monkeypatch.setattr("builtins.open", fake_open)
    assert osc._write("hello") is True
    assert streams[0].data == b"hello"


def test_write_falls_back_to_standard_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_open(*args: object, **kwargs: object) -> io.BytesIO:
        raise OSError("No controlling terminal")

    monkeypatch.setattr("builtins.open", fake_open)
    stdout_buffer = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", FakeStdio(tty=True, buffer=stdout_buffer))
    monkeypatch.setattr(sys, "stderr", FakeStdio(tty=False))

    assert osc._write("hello") is True
    assert stdout_buffer.getvalue() == b"hello"


def test_write_returns_false_without_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_open(*args: object, **kwargs: object) -> io.BytesIO:
        raise OSError("No controlling terminal")

    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr(sys, "stdout", FakeStdio(tty=False))
    monkeypatch.setattr(sys, "stderr", FakeStdio(tty=False))

    assert osc._write("hello") is False


def test_write_skips_broken_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_open(*args: object, **kwargs: object) -> io.BytesIO:
        raise OSError("No controlling terminal")

    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr(sys, "stdout", ClosedStdio(tty=True))
    monkeypatch.setattr(sys, "stderr", FakeStdio(tty=True, buffer=BrokenBuffer()))

    assert osc._write("hello") is False


def test_write_uses_second_stream_if_first_write_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_open(*args: object, **kwargs: object) -> io.BytesIO:
        raise OSError("No controlling terminal")

    monkeypatch.setattr("builtins.open", fake_open)
    stderr_buffer = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", FakeStdio(tty=True, buffer=BrokenBuffer()))
    monkeypatch.setattr(sys, "stderr", FakeStdio(tty=True, buffer=stderr_buffer))

    assert osc._write("hello") is True
    assert stderr_buffer.getvalue() == b"hello"


@pytest.mark.asyncio
async def test_send_requires_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(osc, "detect_protocol", lambda env=None: None)
    backend = OSCNotificationCenter("Test")

    with pytest.raises(RuntimeError):
        await backend._send(Notification(title="Title", message="Message"))


@pytest.mark.asyncio
async def test_send_raises_when_write_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(osc, "_write", lambda sequence: False)
    backend = OSCNotificationCenter("Test")
    backend.protocol = "osc9"

    with pytest.raises(OSError):
        await backend._send(Notification(title="Title", message="Message"))


@pytest.mark.asyncio
async def test_authorisation_clearing_and_capabilities() -> None:
    backend = OSCNotificationCenter("Test")

    assert await backend.request_authorisation() is True
    assert await backend.has_authorisation() is True
    assert await backend.get_capabilities() == {Capability.TITLE, Capability.MESSAGE}

    await backend.clear("missing")
    await backend.clear_all()


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS backend selection")
def test_backend_selection_falls_back_to_terminal() -> None:
    from desktop_notifier import main
    from desktop_notifier.backends.dummy import DummyNotificationCenter

    bundle_patch = patch(
        "desktop_notifier.backends.macos_support.is_bundle", return_value=False
    )
    available_patch = patch(
        "desktop_notifier.backends.osc.is_available", return_value=True
    )
    with bundle_patch, available_patch:
        assert main.get_backend_class() is OSCNotificationCenter

    unavailable_patch = patch(
        "desktop_notifier.backends.osc.is_available", return_value=False
    )
    with bundle_patch, unavailable_patch:
        assert main.get_backend_class() is DummyNotificationCenter
