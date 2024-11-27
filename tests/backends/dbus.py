from __future__ import annotations

from desktop_notifier import DesktopNotifier, DispatchedNotification
from desktop_notifier.backends.dbus import (
    NOTIFICATION_CLOSED_DISMISSED,
    DBusDesktopNotifier,
)


def simulate_clicked(
    notifier: DesktopNotifier, dispatched_notification: DispatchedNotification
) -> None:
    assert isinstance(notifier._backend, DBusDesktopNotifier)
    assert isinstance(dispatched_notification, DispatchedNotification)

    nid = int(dispatched_notification.identifier)
    notifier._backend._on_action(nid, "default")

    # Any closing of the notification also triggers a dismissed event.
    notifier._backend._on_closed(nid, NOTIFICATION_CLOSED_DISMISSED)


def simulate_dismissed(
    notifier: DesktopNotifier, dispatched_notification: DispatchedNotification
) -> None:
    assert isinstance(notifier._backend, DBusDesktopNotifier)
    assert isinstance(dispatched_notification, DispatchedNotification)

    nid = int(dispatched_notification.identifier)
    notifier._backend._on_closed(nid, NOTIFICATION_CLOSED_DISMISSED)


def simulate_button_pressed(
    notifier: DesktopNotifier,
    dispatched_notification: DispatchedNotification,
    button_identifier: str,
) -> None:
    assert isinstance(notifier._backend, DBusDesktopNotifier)
    assert isinstance(dispatched_notification, DispatchedNotification)

    nid = int(dispatched_notification.identifier)
    notifier._backend._on_action(nid, button_identifier)

    # Any closing of the notification also triggers a dismissed event.
    notifier._backend._on_closed(nid, NOTIFICATION_CLOSED_DISMISSED)


def simulate_replied(
    notifier: DesktopNotifier,
    dispatched_notification: DispatchedNotification,
    reply: str,
) -> None:
    raise NotImplementedError("Relied callbacks on supported on Linux")
