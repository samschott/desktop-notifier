import sys
import time

import pytest

from desktop_notifier import (
    DEFAULT_SOUND,
    Button,
    DesktopNotifierSync,
    DispatchedNotification,
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
    dispatched_notification = notifier_sync.send(
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
    assert isinstance(dispatched_notification, DispatchedNotification)

    wait_for_notifications(notifier_sync)

    current_notifications = notifier_sync.get_current_notifications()
    assert dispatched_notification.identifier in current_notifications


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

    assert isinstance(n0, DispatchedNotification)
    assert isinstance(n1, DispatchedNotification)

    wait_for_notifications(notifier_sync, 2)

    nlist0 = notifier_sync.get_current_notifications()
    assert len(nlist0) == 2
    assert n0.identifier in nlist0
    assert n1.identifier in nlist0

    notifier_sync.clear(n0.identifier)

    wait_for_notifications(notifier_sync, 1)

    nlist1 = notifier_sync.get_current_notifications()
    assert len(nlist1) == 1
    assert n0.identifier not in nlist1
    assert n1.identifier in nlist1


def test_clear_all(notifier_sync: DesktopNotifierSync) -> None:
    n0 = notifier_sync.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )
    n1 = notifier_sync.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
    )

    assert isinstance(n0, DispatchedNotification)
    assert isinstance(n1, DispatchedNotification)

    wait_for_notifications(notifier_sync, 2)

    current_notifications = notifier_sync.get_current_notifications()
    assert len(current_notifications) == 2
    assert n0.identifier in current_notifications
    assert n1.identifier in current_notifications

    notifier_sync.clear_all()

    wait_for_notifications(notifier_sync, 0)

    assert len(notifier_sync.get_current_notifications()) == 0
