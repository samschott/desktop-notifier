import asyncio
import sys
import time
from pathlib import Path

import pytest

from desktop_notifier import (
    DEFAULT_SOUND,
    Attachment,
    Button,
    DesktopNotifier,
    Icon,
    ReplyField,
    Sound,
    Urgency,
)


async def wait_for_notifications(
    notifier: DesktopNotifier, notification_count: int = 1, timeout_sec: float = 2.0
) -> None:
    t0 = time.monotonic()

    while time.monotonic() - t0 < timeout_sec:
        if len(await notifier.get_current_notifications()) == notification_count:
            return
        await asyncio.sleep(0.2)

    raise TimeoutError("Timed out while waiting for notifications")


@pytest.mark.asyncio
async def test_request_authorisation(notifier: DesktopNotifier) -> None:
    """
    Authorization should already be grated when setting up the test environment.
    Check that calling request_authorisation returns true.
    """
    if not await notifier.has_authorisation():
        pytest.skip("Not authorised and we cannot request authorisation in test")

    has_authorisation = await notifier.request_authorisation()
    assert has_authorisation


@pytest.mark.asyncio
async def test_send(notifier: DesktopNotifier) -> None:
    notification = await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
        urgency=Urgency.Critical,
        buttons=[
            Button(title="Mark as read", on_pressed=lambda: print("Marked as read"))
        ],
        reply_field=ReplyField(
            title="Reply",
            button_title="Send",
            on_replied=lambda text: print("Brutus replied:", text),
        ),
        on_dispatched=lambda: print("Notification showing"),
        on_clicked=lambda: print("Notification clicked"),
        on_dismissed=lambda: print("Notification dismissed"),
        sound=DEFAULT_SOUND,
        thread="test_notifications",
        timeout=5,
    )
    await wait_for_notifications(notifier)
    assert notification in await notifier.get_current_notifications()


@pytest.mark.asyncio
async def test_icon_name(notifier: DesktopNotifier) -> None:
    await notifier.send(
        title="Julius Caesar", message="Et tu, Brute?", icon=Icon(name="call-start")
    )


@pytest.mark.asyncio
async def test_icon_path(notifier: DesktopNotifier) -> None:
    await notifier.send(
        title="Julius Caesar", message="Et tu, Brute?", icon=Icon(path=Path("/blue"))
    )


@pytest.mark.asyncio
async def test_icon_uri(notifier: DesktopNotifier) -> None:
    await notifier.send(
        title="Julius Caesar", message="Et tu, Brute?", icon=Icon(uri="file:///blue")
    )


@pytest.mark.asyncio
async def test_sound_name(notifier: DesktopNotifier) -> None:
    await notifier.send(
        title="Julius Caesar", message="Et tu, Brute?", sound=Sound(name="Tink")
    )


@pytest.mark.asyncio
async def test_sound_path(notifier: DesktopNotifier) -> None:
    await notifier.send(
        title="Julius Caesar", message="Et tu, Brute?", sound=Sound(path=Path("/blue"))
    )


@pytest.mark.asyncio
async def test_sound_uri(notifier: DesktopNotifier) -> None:
    await notifier.send(
        title="Julius Caesar", message="Et tu, Brute?", sound=Sound(uri="file:///blue")
    )


@pytest.mark.asyncio
async def test_attachment_path(notifier: DesktopNotifier) -> None:
    await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
        attachment=Attachment(path=Path("/blue")),
    )


@pytest.mark.asyncio
async def test_attachment_uri(notifier: DesktopNotifier) -> None:
    await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
        attachment=Attachment(uri="file:///blue"),
    )


@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Clearing individual notifications is broken on Windows",
)
async def test_clear(notifier: DesktopNotifier) -> None:
    n0 = await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )
    n1 = await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )
    await wait_for_notifications(notifier, 2)
    current_notifications = await notifier.get_current_notifications()

    assert n0 in current_notifications
    assert n1 in current_notifications

    await notifier.clear(n0)
    assert n0 not in await notifier.get_current_notifications()


@pytest.mark.asyncio
async def test_clear_all(notifier: DesktopNotifier) -> None:
    n0 = await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )
    n1 = await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )
    await wait_for_notifications(notifier, 2)
    current_notifications = await notifier.get_current_notifications()

    assert n0 in current_notifications
    assert n1 in current_notifications

    await notifier.clear_all()
    assert len(await notifier.get_current_notifications()) == 0
