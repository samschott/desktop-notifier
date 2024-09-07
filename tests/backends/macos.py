from __future__ import annotations

from unittest.mock import Mock

from rubicon.objc.api import Block, ObjCClass
from rubicon.objc.runtime import load_library

from desktop_notifier import DesktopNotifier
from desktop_notifier.backends.macos import (
    CocoaNotificationCenter,
    ReplyActionIdentifier,
)

foundation = load_library("Foundation")
uns = load_library("UserNotifications")

UNNotificationDefaultActionIdentifier = (
    "com.apple.UNNotificationDefaultActionIdentifier"
)
UNNotificationDismissActionIdentifier = (
    "com.apple.UNNotificationDismissActionIdentifier"
)

NSDate = ObjCClass("NSDate")
UNNotification = ObjCClass("UNNotification")
UNNotificationRequest = ObjCClass("UNNotificationRequest")
UNNotificationResponse = ObjCClass("UNNotificationResponse")
UNMutableNotificationContent = ObjCClass("UNMutableNotificationContent")


def simulate_clicked(notifier: DesktopNotifier, identifier: str) -> None:
    _send_response(notifier._backend, identifier, UNNotificationDefaultActionIdentifier)


def simulate_dismissed(notifier: DesktopNotifier, identifier: str) -> None:
    _send_response(notifier._backend, identifier, UNNotificationDismissActionIdentifier)


def simulate_button_pressed(
    notifier: DesktopNotifier, identifier: str, button_identifier: str
) -> None:
    _send_response(notifier._backend, identifier, button_identifier)


def simulate_replied(notifier: DesktopNotifier, identifier: str, reply: str) -> None:
    _send_response(notifier._backend, identifier, ReplyActionIdentifier, reply)


def _send_response(
    backend: CocoaNotificationCenter,
    identifier: str,
    action_identifier: str,
    response_text: str | None = None,
) -> UNNotificationResponse:
    content = UNMutableNotificationContent.alloc().init()
    request = UNNotificationRequest.requestWithIdentifier(
        identifier, content=content, trigger=None
    )
    notification = UNNotification.alloc().initWithNotificationRequest(
        request,
        date=NSDate.date(),
        sourceIdentifier="cocoa-notification-test",
        intentIdentifiers=None,
    )
    response = UNNotificationResponse.alloc().initWithNotification(
        notification, actionIdentifier=action_identifier
    )
    if response_text is not None:
        response.userText = response_text

    mock_completion_handler = Mock()

    backend.nc_delegate.userNotificationCenter_didReceiveNotificationResponse_withCompletionHandler_(
        backend.nc, response, Block(mock_completion_handler, None)
    )

    mock_completion_handler.assert_called()
