# -*- coding: utf-8 -*-
"""
This module handles desktop notifications and supports multiple backends, depending on
the platform.
"""

# system imports
import os
import platform
from threading import RLock
import logging
import asyncio
from typing import Type, Optional, Dict, Callable, Coroutine, List, Any, TypeVar

try:
    from importlib.resources import files  # type: ignore
except ImportError:
    from importlib_resources import files  # type: ignore


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

logger = logging.getLogger(__name__)

T = TypeVar("T")

PYTHON_ICON_PATH = os.path.join(files("desktop_notifier"), "resources", "python.png")
PYTHON_ICON_URI = f"file://{PYTHON_ICON_PATH}"


def _run_coco_sync(coro: Coroutine[None, None, T]) -> T:
    """
    Runs the given coroutine and returns the result synchronously.
    """

    loop = asyncio.get_event_loop()

    if loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        res = future.result()
    else:
        res = loop.run_until_complete(coro)

    return res


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
        app_icon: Optional[str] = PYTHON_ICON_URI,
        notification_limit: Optional[int] = None,
    ) -> None:
        self._lock = RLock()
        self._impl = Impl(app_name, app_icon, notification_limit)
        self._did_request_authorisation = False

    @property
    def app_name(self) -> str:
        """The application name"""
        return self._impl.app_name

    @app_name.setter
    def app_name(self, value: str) -> None:
        """Setter: app_name"""
        self._impl.app_name = value

    @property
    def app_icon(self) -> Optional[str]:
        """The application icon: a URI for a local file or an icon name."""
        return self._impl.app_icon

    @app_icon.setter
    def app_icon(self, value: str) -> None:
        """Setter: app_icon"""
        self._impl.app_icon = value

    async def request_authorisation(self) -> bool:
        """
        Requests authorisation to send user notifications. This will be automatically
        called for you when sending a notification for the first time but it may be
        useful to call manually to request authorisation in advance.

        On some platforms such as macOS and iOS, a prompt will be shown to the user
        when this method is called for the first time. This method does nothing on
        platforms where user authorisation is not required.

        :returns: Whether authorisation has been granted.
        """

        with self._lock:
            self._did_request_authorisation = True
            return await self._impl.request_authorisation()

    async def has_authorisation(self) -> bool:
        """Returns whether we have authorisation to send notifications."""
        return await self._impl.has_authorisation()

    async def send(
        self,
        title: str,
        message: str,
        urgency: NotificationLevel = NotificationLevel.Normal,
        icon: Optional[str] = None,
        buttons: Optional[Dict[str, Callable[[], Any]]] = None,
        reply_field: bool = False,
        on_clicked: Optional[Callable[[], Any]] = None,
        on_dismissed: Optional[Callable[[], Any]] = None,
        on_replied: Optional[Callable[[str], Any]] = None,
        attachment: Optional[str] = None,
        sound: bool = False,
        thread: Optional[str] = None,
    ) -> Notification:
        """
        Sends a desktop notification. Some arguments may be ignored, depending on the
        backend.

        :param title: Notification title.
        :param message: Notification message.
        :param urgency: Notification level: low, normal or critical. This may be
            interpreted differently by some implementations, for instance causing the
            notification to remain visible for longer, or may be ignored.
        :param icon: URI or icon name to use for the notification, typically the app
            icon. This will replace the icon specified by :attr:`app_icon`. Will be
            ignored on macOS.
        :param buttons: A dictionary with button titles and callbacks to show in the
            notification. This is ignored by some implementations.
        :param reply_field: Whether to show a reply field, for instance for a chat
            message. This is ignored on Linux.
        :param on_clicked: Callback to call when the notification is clicked. The
            callback will be called without any arguments. This is ignored by some
            implementations.
        :param on_dismissed: Callback to call when the notification is dismissed. The
            callback will be called without any arguments. This is ignored by some
            implementations.
        :param on_replied: If ``reply_field`` is True, a callback to call once the
            user has replied. The callback will be called a single argument: a string
            with the user reply.
        :param attachment: A path to an attachment for the notification such as an
            image, movie, or audio file. A preview of this attachment may be displayed
            together with the notification. Different platforms and Linux notification
            servers support different types of attachments. Please consult the platform
            support section of the documentation.
        :param sound: Whether to play a sound when the notification is shown. The
            platform's default sound will be used, where available.
        :param thread: An identifier to group related notifications together. This is
            ignored on Linux.

        :returns: The scheduled notification instance.
        """

        notification = Notification(
            title,
            message,
            urgency,
            icon,
            buttons,
            reply_field,
            on_clicked,
            on_dismissed,
            on_replied,
            attachment,
            sound,
            thread,
        )

        with self._lock:

            if not self._did_request_authorisation:
                await self.request_authorisation()

            await self._impl.send(notification)

            return notification

    def send_sync(
        self,
        title: str,
        message: str,
        urgency: NotificationLevel = NotificationLevel.Normal,
        icon: Optional[str] = None,
        buttons: Optional[Dict[str, Callable[[], Any]]] = None,
        reply_field: bool = False,
        on_clicked: Optional[Callable[[], Any]] = None,
        on_dismissed: Optional[Callable[[], Any]] = None,
        on_replied: Optional[Callable[[str], Any]] = None,
        attachment: Optional[str] = None,
        sound: bool = False,
        thread: Optional[str] = None,
    ) -> Notification:
        """
        Synchronous call of :meth:`send`, for use without an asyncio event loop.

        :returns: The scheduled notification instance.
        """

        coro = self.send(
            title,
            message,
            urgency,
            icon,
            buttons,
            reply_field,
            on_clicked,
            on_dismissed,
            on_replied,
            attachment,
            sound,
            thread,
        )

        return _run_coco_sync(coro)

    @property
    def current_notifications(self) -> List[Notification]:
        """A list of all currently displayed notifications for this app"""
        return self._impl.current_notifications

    async def clear(self, notification: Notification) -> None:
        """
        Removes the given notification from the notification center.

        :param notification: Notification to clear.
        """
        with self._lock:
            await self._impl.clear(notification)

    async def clear_all(self) -> None:
        """
        Removes all currently displayed notifications for this app from the notification
        center.
        """
        with self._lock:
            await self._impl.clear_all()
