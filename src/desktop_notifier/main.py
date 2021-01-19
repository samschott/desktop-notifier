# -*- coding: utf-8 -*-
"""
This module handles desktop notifications and supports multiple backends, depending on
the platform.
"""

# system imports
import platform
from threading import Lock
from typing import Optional, Dict, Callable

# local imports
from .base import DesktopNotifierBase, NotificationLevel, Notification


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

    :param app_name: Name of app which sends notifications.
    """

    _impl: DesktopNotifierBase

    def __init__(self, app_name: str = "Python") -> None:
        self._lock = Lock()

        if platform.system() == "Darwin":
            from .macos import Impl
        elif platform.system() == "Linux":
            from .linux import Impl  # type: ignore
        else:
            Impl = DesktopNotifierBase  # type: ignore

        self._impl = Impl(app_name)

    def send(
        self,
        title: str,
        message: str,
        urgency: NotificationLevel = NotificationLevel.Normal,
        icon: Optional[str] = None,
        action: Optional[Callable] = None,
        buttons: Optional[Dict[str, Callable]] = None,
    ) -> None:
        """
        Sends a desktop notification. Some arguments may be ignored, depending on the
        backend.

        :param title: Notification title.
        :param message: Notification message.
        :param urgency: Notification level: low, normal or critical. This is ignored by
            some implementations.
        :param icon: Path to an icon to use for the notification, typically the app
            icon. This is ignored by some implementations, e.g., on macOS where the icon
            of the app bundle is always used.
        :param action: Handler to call when the notification is clicked. This is ignored
            by some implementations.
        :param buttons: A dictionary with button names and callbacks to show in the
            notification. This is ignored by some implementations.
        """
        notification = Notification(title, message, urgency, icon, action, buttons)

        with self._lock:
            self._impl.send(notification)
