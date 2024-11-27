from __future__ import annotations

from unittest.mock import Mock

from rubicon.objc.api import Block, ObjCClass
from rubicon.objc.runtime import load_library

from desktop_notifier import DesktopNotifier, DispatchedNotification
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


def simulate_clicked(
    notifier: DesktopNotifier, dispatched_notification: DispatchedNotification
) -> None:
    assert isinstance(notifier._backend, CocoaNotificationCenter)
    assert isinstance(dispatched_notification, DispatchedNotification)
    _send_response(
        notifier._backend,
        dispatched_notification,
        UNNotificationDefaultActionIdentifier,
    )


def simulate_dismissed(
    notifier: DesktopNotifier, dispatched_notification: DispatchedNotification
) -> None:
    assert isinstance(notifier._backend, CocoaNotificationCenter)
    assert isinstance(dispatched_notification, DispatchedNotification)
    _send_response(
        notifier._backend,
        dispatched_notification,
        UNNotificationDismissActionIdentifier,
    )


def simulate_button_pressed(
    notifier: DesktopNotifier,
    dispatched_notification: DispatchedNotification,
    button_identifier: str,
) -> None:
    assert isinstance(notifier._backend, CocoaNotificationCenter)
    assert isinstance(dispatched_notification, DispatchedNotification)
    _send_response(notifier._backend, dispatched_notification, button_identifier)


def simulate_replied(
    notifier: DesktopNotifier,
    dispatched_notification: DispatchedNotification,
    reply: str,
) -> None:
    assert isinstance(notifier._backend, CocoaNotificationCenter)
    assert isinstance(dispatched_notification, DispatchedNotification)
    _send_response(
        notifier._backend, dispatched_notification, ReplyActionIdentifier, reply
    )


def _send_response(
    backend: CocoaNotificationCenter,
    dispatched_notification: DispatchedNotification,
    action_identifier: str,
    response_text: str | None = None,
) -> None:
    identifier = dispatched_notification.identifier

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
