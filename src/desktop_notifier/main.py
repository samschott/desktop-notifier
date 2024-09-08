# -*- coding: utf-8 -*-
"""
Asynchronous desktop notification API
"""
from __future__ import annotations

import asyncio
import logging
import platform
import warnings
from pathlib import Path
from typing import Any, Callable, Sequence, Type, TypeVar
from urllib import parse

from packaging.version import Version

from .backends.base import DesktopNotifierBackend
from .common import (
    DEFAULT_ICON,
    DEFAULT_SOUND,
    Attachment,
    Button,
    Capability,
    Icon,
    Notification,
    ReplyField,
    Sound,
    Urgency,
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


def get_backend_class() -> Type[DesktopNotifierBackend]:
    """
    Return the backend class depending on the platform and version.

    :returns: A desktop notification backend suitable for the current platform.
    :raises RuntimeError: when passing ``macos_legacy = True`` on macOS 12.0 and later.
    """
    if platform.system() == "Darwin":
        from .backends.macos_support import is_bundle, is_signed_bundle, macos_version

        has_unusernotificationcenter = macos_version >= Version("10.14")

        if has_unusernotificationcenter and is_bundle():
            from .backends.macos import CocoaNotificationCenter

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

            from .backends.dummy import DummyNotificationCenter

            return DummyNotificationCenter

    elif platform.system() == "Linux":
        from .backends.dbus import DBusDesktopNotifier

        return DBusDesktopNotifier

    elif platform.system() == "Windows" and Version(platform.version()) >= Version(
        "10.0.10240"
    ):
        from .backends.winrt import WinRTDesktopNotifier

        return WinRTDesktopNotifier

    else:
        from .backends.dummy import DummyNotificationCenter

        return DummyNotificationCenter


class DesktopNotifier:
    """Cross-platform desktop notification emitter

    Uses different backends depending on the platform version and available services.
    All implementations will dispatch notifications without an event loop but will
    require a running event loop to execute callbacks when the end user interacts with a
    notification. On Linux, an asyncio event loop is required. On macOS, a CFRunLoop *in
    the main thread* is required. Packages such as :mod:`rubicon.objc` can be used to
    integrate asyncio with a CFRunLoop.

    Callbacks to handle user interactions with a notification can be specified either at
    the class level, where they take the notification identifier as input, or directly
    on the notification itself. The latter will take precedence if set.

    Note that handlers that are directly set on the notification are tied to Python
    notification instance and therefore the app's lifecycle. Handlers that are set on
    the class level may run also for interactions with a notification while the app was
    not running, if DesktopNotifier is instantiated at app startup.

    :param app_name: Name to identify the application in the notification center. On
        Linux, this should correspond to the application name in a desktop entry. On
        macOS, this argument is ignored and the app is identified by the bundle ID of
        the sending program (e.g., Python).
    :param app_icon: Default icon to use for notifications. This should be a
        :class:`desktop_notifier.base.Icon` instance referencing either a file or a
        named system icon. :class:`str` or :class:`pathlib.Path` are also accepted but
        deprecated.
    """

    app_icon: Icon | None

    def __init__(
        self,
        app_name: str = "Python",
        app_icon: Icon | None = DEFAULT_ICON,
        notification_limit: int | None = None,
    ) -> None:
        if notification_limit is not None:
            warnings.warn(
                message="Notification limits have been deprecated and no longer have an effect",
                category=DeprecationWarning,
            )

        self.app_icon = app_icon

        backend = get_backend_class()
        self._backend = backend(app_name)
        self._did_request_authorisation = False

        self._capabilities: frozenset[Capability] | None = None

    @property
    def app_name(self) -> str:
        """The application name"""
        return self._backend.app_name

    @app_name.setter
    def app_name(self, value: str) -> None:
        """Setter: app_name"""
        self._backend.app_name = value

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
        return await self._backend.request_authorisation()

    async def has_authorisation(self) -> bool:
        """Returns whether we have authorisation to send notifications."""
        return await self._backend.has_authorisation()

    async def send_notification(self, notification: Notification) -> str:
        """
        Sends a desktop notification.

        This method does not raise an exception when scheduling the notification fails
        but logs warnings instead.

        Note that even a successfully scheduled notification may not be displayed to the
        user, depending on their notification center settings (for instance if "do not
        disturb" is enabled on macOS).

        :param notification: The notification to send.
        :returns: An identifier for the scheduled notification.
        """
        if not notification.icon:
            object.__setattr__(notification, "icon", self.app_icon)

        # Ask for authorisation if not already done. On some platforms, this will
        # trigger a system dialog to ask the user for permission.
        if not self._did_request_authorisation:
            await self.request_authorisation()
        else:
            logger.debug("Notification center authorisation was already requested")

        # We attempt to send the notification regardless of authorization.
        # The user may have changed settings in the meantime.
        await self._backend.send(notification)

        return notification.identifier

    async def send(
        self,
        title: str,
        message: str,
        urgency: Urgency = Urgency.Normal,
        icon: Icon | None = None,
        buttons: Sequence[Button] = (),
        reply_field: ReplyField | None = None,
        on_clicked: Callable[[], Any] | None = None,
        on_dismissed: Callable[[], Any] | None = None,
        attachment: Attachment | None = None,
        sound: Sound | None = None,
        thread: str | None = None,
        timeout: int = -1,  # in seconds
    ) -> str:
        """
        Sends a desktop notification

        This is a convenience function which creates a
        :class:`desktop_notifier.base.Notification` with the provided arguments and then
        calls :meth:`send_notification`.

        :returns: An identifier for the scheduled notification.
        """
        notification = Notification(
            title,
            message,
            urgency=urgency,
            icon=icon,
            buttons=tuple(buttons),
            reply_field=reply_field,
            on_clicked=on_clicked,
            on_dismissed=on_dismissed,
            attachment=attachment,
            sound=sound,
            thread=thread,
            timeout=timeout,
        )
        return await self.send_notification(notification)

    async def get_current_notifications(self) -> list[str]:
        """Returns identifiers of all currently displayed notifications for this app."""
        return await self._backend.get_current_notifications()

    async def clear(self, identifier: str) -> None:
        """
        Removes the given notification from the notification center.

        :param identifier: Notification identifier.
        """
        await self._backend.clear(identifier)

    async def clear_all(self) -> None:
        """
        Removes all currently displayed notifications for this app from the notification
        center.
        """
        await self._backend.clear_all()

    async def get_capabilities(self) -> frozenset[Capability]:
        """
        Returns which functionality is supported by the implementation.
        """
        if not self._capabilities:
            self._capabilities = await self._backend.get_capabilities()
        return self._capabilities

    @property
    def on_clicked(self) -> Callable[[str], Any] | None:
        """
        A method to call when a notification is clicked

        The method must take the notification identifier as a single argument.

        If the notification itself already specifies an on_clicked handler, it will be
        used instead of the class-level handler.
        """
        return self._backend.on_clicked

    @on_clicked.setter
    def on_clicked(self, handler: Callable[[str], Any] | None) -> None:
        self._backend.on_clicked = handler

    @property
    def on_dismissed(self) -> Callable[[str], Any] | None:
        """
        A method to call when a notification is dismissed

        The method must take the notification identifier as a single argument.

        If the notification itself already specifies an on_dismissed handler, it will be
        used instead of the class-level handler.
        """
        return self._backend.on_dismissed

    @on_dismissed.setter
    def on_dismissed(self, handler: Callable[[str], Any] | None) -> None:
        self._backend.on_dismissed = handler

    @property
    def on_button_pressed(self) -> Callable[[str, str], Any] | None:
        """
        A method to call when a notification is dismissed

        The method must take the notification identifier and the button number as
        arguments.

        If the notification button itself already specifies an on_pressed handler, it
        will be used instead of the class-level handler.
        """
        return self._backend.on_button_pressed

    @on_button_pressed.setter
    def on_button_pressed(self, handler: Callable[[str, str], Any] | None) -> None:
        self._backend.on_button_pressed = handler

    @property
    def on_replied(self) -> Callable[[str, str], Any] | None:
        """
        A method to call when a user responds through the reply field of a notification

        The method must take the notification identifier and input text as arguments.

        If the notification's reply field itself already specifies an on_replied
        handler, it will be used instead of the class-level handler.
        """
        return self._backend.on_replied

    @on_replied.setter
    def on_replied(self, handler: Callable[[str, str], Any] | None) -> None:
        self._backend.on_replied = handler
