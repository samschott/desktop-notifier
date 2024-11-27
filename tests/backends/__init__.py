import platform

from desktop_notifier import DesktopNotifier, DispatchedNotification

__all__ = [
    "simulate_button_pressed",
    "simulate_clicked",
    "simulate_replied",
    "simulate_dismissed",
]

if platform.system() == "Darwin":
    from .macos import (
        simulate_button_pressed,
        simulate_clicked,
        simulate_dismissed,
        simulate_replied,
    )
elif platform.system() == "Linux":
    from .dbus import (
        simulate_button_pressed,
        simulate_clicked,
        simulate_dismissed,
        simulate_replied,
    )
else:

    def simulate_clicked(
        notifier: DesktopNotifier, dispatched_notification: DispatchedNotification
    ) -> None:
        raise NotImplementedError(f"{platform.system()} is not supported")

    def simulate_dismissed(
        notifier: DesktopNotifier, dispatched_notification: DispatchedNotification
    ) -> None:
        raise NotImplementedError(f"{platform.system()} is not supported")

    def simulate_button_pressed(
        notifier: DesktopNotifier,
        dispatched_notification: DispatchedNotification,
        button_identifier: str,
    ) -> None:
        raise NotImplementedError(f"{platform.system()} is not supported")

    def simulate_replied(
        notifier: DesktopNotifier,
        dispatched_notification: DispatchedNotification,
        reply: str,
    ) -> None:
        raise NotImplementedError(f"{platform.system()} is not supported")
