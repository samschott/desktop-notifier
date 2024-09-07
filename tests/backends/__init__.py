import platform

from desktop_notifier import DesktopNotifier

if platform.system() == "Darwin":
    from .macos import (
        simulate_button_pressed,
        simulate_clicked,
        simulate_dismissed,
        simulate_replied,
    )
else:

    def simulate_clicked(notifier: DesktopNotifier, identifier: str) -> None:
        raise NotImplementedError(f"{platform.system()} is not supported")

    def simulate_dismissed(notifier: DesktopNotifier, identifier: str) -> None:
        raise NotImplementedError(f"{platform.system()} is not supported")

    def simulate_button_pressed(
        notifier: DesktopNotifier, identifier: str, button_identifier: str
    ) -> None:
        raise NotImplementedError(f"{platform.system()} is not supported")

    def simulate_replied(
        notifier: DesktopNotifier, identifier: str, reply: str
    ) -> None:
        raise NotImplementedError(f"{platform.system()} is not supported")
