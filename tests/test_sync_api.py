import sys
import time

import pytest

from desktop_notifier import (
    DEFAULT_SOUND,
    Button,
    DesktopNotifierSync,
    ReplyField,
    Urgency,
)


def wait_for_notifications(
    notifier: DesktopNotifierSync, notification_count: int = 1, timeout_sec: float = 2.0
) -> None:
    t0 = time.monotonic()

    while time.monotonic() - t0 < timeout_sec:
        if len(notifier.get_current_notifications()) == notification_count:
            return
        time.sleep(0.2)

    raise TimeoutError("Timed out while waiting for notifications")


def test_send(notifier_sync: DesktopNotifierSync) -> None:
    notification = notifier_sync.send(
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
    wait_for_notifications(notifier_sync)
    assert notification in notifier_sync.get_current_notifications()


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Clearing individual notifications is broken on Windows",
)
def test_clear(notifier_sync: DesktopNotifierSync) -> None:
    n0 = notifier_sync.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )
    n1 = notifier_sync.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )
    wait_for_notifications(notifier_sync, 2)
    current_notifications = notifier_sync.get_current_notifications()

    assert n0 in current_notifications
    assert n1 in current_notifications

    notifier_sync.clear(n0)
    assert n0 not in notifier_sync.get_current_notifications()


def test_clear_all(notifier_sync: DesktopNotifierSync) -> None:
    n0 = notifier_sync.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )
    n1 = notifier_sync.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )
    wait_for_notifications(notifier_sync, 2)
    current_notifications = notifier_sync.get_current_notifications()

    assert n0 in current_notifications
    assert n1 in current_notifications

    notifier_sync.clear_all()
    assert len(notifier_sync.get_current_notifications()) == 0
