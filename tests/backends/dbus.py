from __future__ import annotations

from desktop_notifier import DesktopNotifier
from desktop_notifier.backends.dbus import NOTIFICATION_CLOSED_DISMISSED


def simulate_clicked(notifier: DesktopNotifier, identifier: str) -> None:
    nid = notifier._backend._platform_to_interface_notification_identifier.inverse[
        identifier
    ]
    notifier._backend._on_action(nid, "default")


def simulate_dismissed(notifier: DesktopNotifier, identifier: str) -> None:
    nid = notifier._backend._platform_to_interface_notification_identifier.inverse[
        identifier
    ]
    notifier._backend._on_closed(nid, NOTIFICATION_CLOSED_DISMISSED)


def simulate_button_pressed(
    notifier: DesktopNotifier, identifier: str, button_identifier: str
) -> None:
    nid = notifier._backend._platform_to_interface_notification_identifier.inverse[
        identifier
    ]
    notifier._backend._on_action(nid, button_identifier)


def simulate_replied(notifier: DesktopNotifier, identifier: str, reply: str) -> None:
    raise NotImplementedError("Relied callbacks on supported on Linux")
