from desktop_notifier import DesktopNotifier
from desktop_notifier.backends.winrt import (
    DEFAULT_ACTION,
    REPLY_ACTION,
    BUTTON_ACTION_PREFIX,
    REPLY_TEXTBOX_NAME,
)

from winrt.windows.ui.notifications import (
    ToastActivatedEventArgs,
    ToastDismissalReason,
    ToastDismissedEventArgs,
    ToastNotification,
)
from winrt.windows.foundation.interop import box
from winrt.windows.data.xml.dom import XmlDocument


def simulate_clicked(notifier: DesktopNotifier, identifier: str) -> None:
    sender = ToastNotification(XmlDocument())
    sender.tag = identifier
    activated_args = ToastActivatedEventArgs()
    activated_args.arguments = DEFAULT_ACTION
    notifier._backend._on_activated(sender, box(activated_args))


def simulate_dismissed(notifier: DesktopNotifier, identifier: str) -> None:
    sender = ToastNotification(XmlDocument())
    sender.tag = identifier
    dismissed_args = ToastDismissedEventArgs()
    dismissed_args.reason = ToastDismissalReason.USER_CANCELED
    notifier._backend._on_dismissed(sender, dismissed_args)


def simulate_button_pressed(
    notifier: DesktopNotifier, identifier: str, button_identifier: str
) -> None:
    sender = ToastNotification(XmlDocument())
    sender.tag = identifier
    activated_args = ToastActivatedEventArgs()
    activated_args.arguments = BUTTON_ACTION_PREFIX + button_identifier
    notifier._backend._on_activated(sender, box(activated_args))


def simulate_replied(notifier: DesktopNotifier, identifier: str, reply: str) -> None:
    sender = ToastNotification(XmlDocument())
    sender.tag = identifier
    activated_args = ToastActivatedEventArgs()
    activated_args.arguments = REPLY_ACTION
    activated_args.user_input[REPLY_TEXTBOX_NAME] = box(reply)
    notifier._backend._on_activated(sender, box(activated_args))
