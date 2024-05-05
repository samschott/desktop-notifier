import sys
import pytest

from desktop_notifier import Urgency, Button, ReplyField


@pytest.mark.asyncio
async def test_request_authorisation(notifier):
    assert await notifier.request_authorisation()
    assert await notifier.has_authorisation()


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
        sound=True,
        thread="test_notifications",
        timeout=5,
    )
    assert notification in notifier.current_notifications
    assert notification.identifier != ""


def test_send_sync(notifier):
    notification = notifier.send_sync(
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
        sound=True,
        thread="test_notifications",
        timeout=5,
    )
    assert notification in notifier.current_notifications
    assert notification.identifier != ""


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
