# -*- coding: utf-8 -*-
"""
This module handles desktop notifications and supports multiple backends, depending on
the platform.
"""

# system imports
import os
import platform
from threading import Lock
from typing import Type, Optional, Dict, Callable, List

# external imports
from packaging.version import Version

# local imports
from .base import NotificationLevel, Notification, DesktopNotifierBase


Impl: Type[DesktopNotifierBase]

if os.environ.get("CI", False):
    # don't attempt to initialise notification center in CIs such as github actions
    # this may otherwise lead to segfaults on macOS test runners
    from .dummy import DummyNotificationCenter as Impl

elif platform.system() == "Darwin":

    macos_version, *_ = platform.mac_ver()

    if Version(macos_version) >= Version("10.14.0"):
        from .macos import CocoaNotificationCenter as Impl
    else:
        from .macos_legacy import CocoaNotificationCenterLegacy as Impl

elif platform.system() == "Linux":
    from .dbus import DBusDesktopNotifier as Impl

else:
    from .dummy import DummyNotificationCenter as Impl


__all__ = [
    "Notification",
    "NotificationLevel",
    "DesktopNotifier",
]


class DesktopNotifier:
    """Cross-platform desktop notification emitter

    Uses different backends depending on the platform version and available services.
    All implementations will dispatch notifications without an event loop but will
    require a running event loop to execute callbacks when the end user interacts with a
    notification. On Linux, a asyncio event loop is required. On macOS, a CFRunLoop *in
    the main thread* is required. Packages such as :mod:`rubicon.objc` can be used to
    integrate asyncio with a CFRunLoop.

    :param app_name: Name to identify the application in the notification center. On
        Linux, this should correspond to the application name in a desktop entry. On
        macOS, this argument is ignored and the app is identified by the bundle ID of
        the sending program (e.g., Python).
    :param app_icon: Default icon to use for notifications. This may be be either an URI
        (file:// is the only URI schema supported right now) or a name in a
        freedesktop.org-compliant icon theme. On macOS, this argument is ignored and the
        app icon is identified by the bundle ID of the sending program (e.g., Python).
    :param notification_limit: Maximum number of notifications to keep in the system's
        notification center. This may be ignored by some implementations.
    """

    def __init__(
        self,
        app_name: str = "Python",
        app_icon: Optional[str] = None,
        notification_limit: Optional[int] = None,
    ) -> None:
        self._lock = Lock()
        self._impl = Impl(app_name, app_icon, notification_limit)

    def send(
        self,
        title: str,
        message: str,
        urgency: NotificationLevel = NotificationLevel.Normal,
        icon: Optional[str] = None,
        action: Optional[Callable] = None,
        buttons: Optional[Dict[str, Callable]] = None,
        sound: bool = False,
    ) -> Notification:
        """
        Sends a desktop notification. Some arguments may be ignored, depending on the
        backend.

        :param title: Notification title.
        :param message: Notification message.
        :param urgency: Notification level: low, normal or critical. This may be
            interpreted differently but some implementations, for instance causing the
            notification to remain visible for longer, or may be ignored.
        :param icon: Path to an icon to use for the notification, typically the app
            icon. This is ignored by some implementations, e.g., on macOS where the icon
            of the app bundle is always used.
        :param action: Handler to call when the notification is clicked. This is ignored
            by some implementations.
        :param buttons: A dictionary with button names and callbacks to show in the
            notification. This is ignored by some implementations.
        :param sound: A sound to play when showing the notification. Can be a predefined
            sound or the path to a sound file.

        :returns: The scheduled notification instance.
        """
        notification = Notification(
            title, message, urgency, icon, action, buttons, sound
        )

        with self._lock:
            self._impl.send(notification)

        return notification

    @property
    def current_notifications(self) -> List[Notification]:
        """A list of all currently displayed notifications for this app"""
        return self._impl.current_notifications

    def clear(self, notification: Notification) -> None:
        """
        Removes the given notification from the notification center.

        :param notification: Notification to clear.
        """
        with self._lock:
            self._impl.clear(notification)

    def clear_all(self) -> None:
        """
        Removes all currently displayed notifications for this app from the notification
        center.
        """
        with self._lock:
            self._impl.clear_all()
