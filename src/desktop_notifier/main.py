# -*- coding: utf-8 -*-
"""
Asynchronous desktop notification API
"""

from __future__ import annotations

# system imports
import platform
import logging
import asyncio
import warnings
from urllib import parse
from pathlib import Path
from typing import (
    Type,
    Callable,
    List,
    Any,
    TypeVar,
    Sequence,
)

# external imports
from packaging.version import Version

# local imports
from .base import (
    Capability,
    Urgency,
    Button,
    ReplyField,
    Icon,
    Sound,
    Attachment,
    Notification,
    DesktopNotifierBase,
    DEFAULT_SOUND,
    DEFAULT_ICON,
)

__all__ = [
    "Notification",
    "Button",
    "ReplyField",
    "Icon",
    "Sound",
    "Attachment",
    "Urgency",
    "DesktopNotifier",
    "Capability",
    "DEFAULT_SOUND",
    "DEFAULT_ICON",
]

logger = logging.getLogger(__name__)

T = TypeVar("T")


default_event_loop_policy = asyncio.DefaultEventLoopPolicy()


def get_implementation_class() -> Type[DesktopNotifierBase]:
    """
    Return the backend class depending on the platform and version.

    :returns: A desktop notification backend suitable for the current platform.
    :raises RuntimeError: when passing ``macos_legacy = True`` on macOS 12.0 and later.
    """
    if platform.system() == "Darwin":
        from .macos_support import is_bundle, is_signed_bundle, macos_version

        has_unusernotificationcenter = macos_version >= Version("10.14")

        if has_unusernotificationcenter and is_bundle():
            from .macos import CocoaNotificationCenter

            if not is_signed_bundle():
                logger.warning(
                    "Could not very signature of app bundle, notifications may fail"
                )
            return CocoaNotificationCenter
        else:
            if has_unusernotificationcenter:
                logger.warning(
                    "Notification Center can only be used from an app bundle"
                )
            else:
                logger.warning("Only macOS 10.14 and later are supported")

            from .dummy import DummyNotificationCenter

            return DummyNotificationCenter

    elif platform.system() == "Linux":
        from .dbus import DBusDesktopNotifier

        return DBusDesktopNotifier

    elif platform.system() == "Windows" and Version(platform.version()) >= Version(
        "10.0.10240"
    ):
        from .winrt import WinRTDesktopNotifier

        return WinRTDesktopNotifier

    else:
        from .dummy import DummyNotificationCenter

        return DummyNotificationCenter


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
    :param app_icon: Default icon to use for notifications. This should be a
        :class:`desktop_notifier.base.Icon` instance referencing either a file or a
        named system icon. :class:`str` or :class:`pathlib.Path` are also accepted but
        deprecated.
    :param notification_limit: Maximum number of notifications to keep in the system's
        notification center. This may be ignored by some implementations.
    """

    app_icon: Icon | None

    def __init__(
        self,
        app_name: str = "Python",
        app_icon: Icon | Path | str | None = DEFAULT_ICON,
        notification_limit: int | None = None,
    ) -> None:
        if isinstance(app_icon, str):
            warnings.warn(
                message="Pass an Icon instance instead of a string. "
                "Support for string input will be removed in a future release.",
                category=DeprecationWarning,
            )
            if parse.urlparse(app_icon).hostname != "":
                app_icon = Icon(uri=app_icon)
            else:
                app_icon = Icon(name=app_icon)

        if isinstance(app_icon, Path):
            warnings.warn(
                message="Pass an Icon instance instead of a Path. "
                "Support for string input will be removed in a future release.",
                category=DeprecationWarning,
            )
            app_icon = Icon(path=app_icon)

        self.app_icon = app_icon

        impl_cls = get_implementation_class()
        self._impl = impl_cls(app_name, notification_limit)
        self._did_request_authorisation = False

        self._capabilities: frozenset[Capability] | None = None

    @property
    def app_name(self) -> str:
        """The application name"""
        return self._impl.app_name

    @app_name.setter
    def app_name(self, value: str) -> None:
        """Setter: app_name"""
        self._impl.app_name = value

    async def request_authorisation(self) -> bool:
        """
        Requests authorisation to send user notifications. This will be automatically
        called for you when sending a notification for the first time. It also can be
        called manually to request authorisation in advance.

        On some platforms such as macOS and iOS, a prompt will be shown to the user
        when this method is called for the first time. This method does nothing on
        platforms where user authorisation is not required.

        :returns: Whether authorisation has been granted.
        """
        self._did_request_authorisation = True
        return await self._impl.request_authorisation()

    async def has_authorisation(self) -> bool:
        """Returns whether we have authorisation to send notifications."""
        return await self._impl.has_authorisation()

    async def send_notification(self, notification: Notification) -> Notification:
        """
        Sends a desktop notification.

        This method does not raise an exception when scheduling the notification fails
        but logs warnings instead. If the notification was scheduled successfully, its
        ``identifier`` will be set to the platform's native notification identifier.
        Otherwise, the ``identifier`` will be ``None``.

        Note that even a successfully scheduled notification may not be displayed to the
        user, depending on their notification center settings (for instance if "do not
        disturb" is enabled on macOS).

        :param notification: The notification to send.
        :returns: The passed notification instance with a unique identifier populated.
        """
        if not notification.icon:
            notification.icon = self.app_icon

        # Ask for authorisation if not already done. On some platforms, this will
        # trigger a system dialog to ask the user for permission.
        if not self._did_request_authorisation:
            await self.request_authorisation()

        # We attempt to send the notification regardless of authorization.
        # The user may have changed settings in the meantime.
        await self._impl.send(notification)

        return notification

    async def send(
        self,
        title: str,
        message: str,
        urgency: Urgency = Urgency.Normal,
        icon: str | Icon | None = None,
        buttons: Sequence[Button] = (),
        reply_field: ReplyField | None = None,
        on_clicked: Callable[[], Any] | None = None,
        on_dismissed: Callable[[], Any] | None = None,
        attachment: str | Attachment | None = None,
        sound: bool | Sound | None = None,
        thread: str | None = None,
        timeout: int = -1,
    ) -> Notification:
        """
        Sends a desktop notification

        This is a convenience function which creates a
        :class:`desktop_notifier.base.Notification` with the provided arguments and then
        calls :meth:`send_notification`.

        :returns: The scheduled notification instance.
        """
        notification = Notification(
            title,
            message,
            urgency=urgency,
            icon=icon,
            buttons=buttons,
            reply_field=reply_field,
            on_clicked=on_clicked,
            on_dismissed=on_dismissed,
            attachment=attachment,
            sound=sound,
            thread=thread,
            timeout=timeout,
        )
        return await self.send_notification(notification)

    @property
    def current_notifications(self) -> List[Notification]:
        """A list of all currently displayed notifications for this app"""
        return self._impl.current_notifications

    async def clear(self, notification: Notification) -> None:
        """
        Removes the given notification from the notification center.

        :param notification: Notification to clear.
        """
        await self._impl.clear(notification)

    async def clear_all(self) -> None:
        """
        Removes all currently displayed notifications for this app from the notification
        center.
        """
        await self._impl.clear_all()

    async def get_capabilities(self) -> frozenset[Capability]:
        """
        Returns which functionality is supported by the implementation.
        """
        if not self._capabilities:
            self._capabilities = await self._impl.get_capabilities()
        return self._capabilities
