import sys
import pytest

from pathlib import Path
from desktop_notifier import (
    Urgency,
    Button,
    Icon,
    Sound,
    Attachment,
    ReplyField,
    DEFAULT_SOUND,
    DEFAULT_ICON,
)


@pytest.mark.asyncio
async def test_send(notifier):
    notification = await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
        urgency=Urgency.Critical,
        buttons=[
            Button(
                title="Mark as read",
                on_pressed=lambda: print("Marked as read"),
            )
        ],
        reply_field=ReplyField(
            title="Reply",
            button_title="Send",
            on_replied=lambda text: print("Brutus replied:", text),
        ),
        on_clicked=lambda: print("Notification clicked"),
        on_dismissed=lambda: print("Notification dismissed"),
        sound=DEFAULT_SOUND,
        thread="test_notifications",
        timeout=5,
    )
    assert notification in notifier.current_notifications
    assert notification.identifier != ""


@pytest.mark.asyncio
async def test_default_icon(notifier):
    notification = await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )
    assert notification.icon == DEFAULT_ICON


@pytest.mark.asyncio
async def test_icon_name(notifier):
    await notifier.send(
        title="Julius Caesar", message="Et tu, Brute?", icon=Icon(name="call-start")
    )


@pytest.mark.asyncio
async def test_icon_path(notifier):
    await notifier.send(
        title="Julius Caesar", message="Et tu, Brute?", icon=Icon(path=Path("/blue"))
    )


@pytest.mark.asyncio
async def test_icon_uri(notifier):
    await notifier.send(
        title="Julius Caesar", message="Et tu, Brute?", icon=Icon(uri="file:///blue")
    )


@pytest.mark.asyncio
async def test_sound_name(notifier):
    await notifier.send(
        title="Julius Caesar", message="Et tu, Brute?", sound=Sound(name="Tink")
    )


@pytest.mark.asyncio
async def test_sound_path(notifier):
    await notifier.send(
        title="Julius Caesar", message="Et tu, Brute?", sound=Sound(path=Path("/blue"))
    )


@pytest.mark.asyncio
async def test_sound_uri(notifier):
    await notifier.send(
        title="Julius Caesar", message="Et tu, Brute?", sound=Sound(uri="file:///blue")
    )


@pytest.mark.asyncio
async def test_attachment_path(notifier):
    await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
        attachment=Attachment(path=Path("/blue")),
    )


@pytest.mark.asyncio
async def test_attachment_uri(notifier):
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
async def test_clear(notifier):
    n0 = await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )
    n1 = await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )
    assert n0 in notifier.current_notifications
    assert n1 in notifier.current_notifications

    await notifier.clear(n0)
    assert n0 not in notifier.current_notifications


@pytest.mark.asyncio
async def test_clear_all(notifier):
    n0 = await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )
    n1 = await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )
    assert n0 in notifier.current_notifications
    assert n1 in notifier.current_notifications

    await notifier.clear_all()
    assert len(notifier.current_notifications) == 0
