from __future__ import annotations

from desktop_notifier import DesktopNotifier
from desktop_notifier.backends.dbus import (
    NOTIFICATION_CLOSED_DISMISSED,
    DBusDesktopNotifier,
)


def simulate_clicked(notifier: DesktopNotifier, identifier: str) -> None:
    assert isinstance(notifier._backend, DBusDesktopNotifier)

    nid = notifier._backend._platform_to_interface_notification_identifier.inverse[
        identifier
    ]
    notifier._backend._on_action(nid, "default")

    # Any closing of the notification also triggers a dismissed event.
    notifier._backend._on_closed(nid, NOTIFICATION_CLOSED_DISMISSED)


def simulate_dismissed(notifier: DesktopNotifier, identifier: str) -> None:
    assert isinstance(notifier._backend, DBusDesktopNotifier)

    nid = notifier._backend._platform_to_interface_notification_identifier.inverse[
        identifier
    ]
    notifier._backend._on_closed(nid, NOTIFICATION_CLOSED_DISMISSED)


def simulate_button_pressed(
    notifier: DesktopNotifier, identifier: str, button_identifier: str
) -> None:
    assert isinstance(notifier._backend, DBusDesktopNotifier)

    nid = notifier._backend._platform_to_interface_notification_identifier.inverse[
        identifier
    ]
    notifier._backend._on_action(nid, button_identifier)

    # Any closing of the notification also triggers a dismissed event.
    notifier._backend._on_closed(nid, NOTIFICATION_CLOSED_DISMISSED)


def simulate_replied(notifier: DesktopNotifier, identifier: str, reply: str) -> None:
    assert isinstance(notifier._backend, DBusDesktopNotifier)

    nid = notifier._backend._platform_to_interface_notification_identifier.inverse[
        identifier
    ]
    notifier._backend._on_reply(nid, reply)
