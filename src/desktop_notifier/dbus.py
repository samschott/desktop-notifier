# -*- coding: utf-8 -*-
"""
Notification backend for Linux. Includes an implementation to send desktop notifications
over Dbus. Responding to user interaction with a notification requires a running asyncio
event loop.
"""

# system imports
import asyncio
import logging
from typing import Optional, Coroutine, TypeVar, Callable

# external imports
from dbus_next import Variant  # type: ignore
from dbus_next.aio import MessageBus, ProxyInterface  # type: ignore

# local imports
from .base import Notification, DesktopNotifierBase, NotificationLevel


__all__ = ["DBusDesktopNotifier"]

logger = logging.getLogger(__name__)

T = TypeVar("T")

NOTIFICATION_CLOSED_EXPIRED = 1
NOTIFICATION_CLOSED_DISMISSED = 2
NOTIFICATION_CLOSED_PROGRAMMATICALLY = 3
NOTIFICATION_CLOSED_UNDEFINED = 4


class DBusDesktopNotifier(DesktopNotifierBase):
    """DBus notification backend for Linux

    This implements the org.freedesktop.Notifications standard. The DBUS connection is
    created in a thread with a running asyncio loop to handle clicked notifications.

    :param app_name: The name of the app. If it matches the application name in an
        existing desktop entry, the icon from that entry will be used by default.
    :param app_icon: The default icon to use for notifications. Will take precedence
        over any icon from the desktop file. Should be a URI or a name in a
        freedesktop.org-compliant icon theme.
    :param notification_limit: Maximum number of notifications to keep in the system's
        notification center.
    """

    _to_native_urgency = {
        NotificationLevel.Low: Variant("y", 0),
        NotificationLevel.Normal: Variant("y", 1),
        NotificationLevel.Critical: Variant("y", 2),
    }

    def __init__(
        self,
        app_name: str = "Python",
        app_icon: Optional[str] = None,
        notification_limit: Optional[int] = None,
    ) -> None:
        super().__init__(app_name, app_icon, notification_limit)
        self._loop = asyncio.get_event_loop()
        self.interface: Optional[ProxyInterface] = None

    def request_authorisation(self, callback: Optional[Callable]) -> None:
        """
        Request authorisation to send notifications.
        """
        if callback:
            callback(True, "")

    @property
    def has_authorisation(self) -> bool:
        """
        Whether we have authorisation to send notifications.
        """
        return True

    def _run_coco_sync(self, coro: Coroutine[None, None, T]) -> T:
        """
        Runs the given coroutine and returns the result synchronously.
        """

        if self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            res = future.result()
        else:
            res = self._loop.run_until_complete(coro)

        return res

    async def _init_dbus(self) -> ProxyInterface:

        self.bus = await MessageBus().connect()
        introspection = await self.bus.introspect(
            "org.freedesktop.Notifications", "/org/freedesktop/Notifications"
        )
        self.proxy_object = self.bus.get_proxy_object(
            "org.freedesktop.Notifications",
            "/org/freedesktop/Notifications",
            introspection,
        )
        self.interface = self.proxy_object.get_interface(
            "org.freedesktop.Notifications"
        )

        # Some older interfaces may not support notification actions.

        if hasattr(self.interface, "on_notification_closed"):
            self.interface.on_notification_closed(self._on_closed)

        if hasattr(self.interface, "on_action_invoked"):
            self.interface.on_action_invoked(self._on_action)

        return self.interface

    def _send(
        self,
        notification: Notification,
        notification_to_replace: Optional[Notification],
    ) -> int:
        """
        Synchronously sends a notification via the Dbus interface.

        :param notification: Notification to send.
        :param notification_to_replace: Notification to replace, if any.
        """
        return self._run_coco_sync(
            self._send_async(notification, notification_to_replace)
        )

    async def _send_async(
        self,
        notification: Notification,
        notification_to_replace: Optional[Notification],
    ) -> int:
        """
        Asynchronously sends a notification via the Dbus interface.

        :param notification: Notification to send.
        :param notification_to_replace: Notification to replace, if any.
        """
        if not self.interface:
            self.interface = await self._init_dbus()

        if notification_to_replace:
            replaces_nid = notification_to_replace.identifier
        else:
            replaces_nid = 0

        # Create list of actions with default and user-supplied.
        actions = ["default", "default"]

        for button_name in notification.buttons.keys():
            actions += [button_name, button_name]

        hints = {"urgency": self._to_native_urgency[notification.urgency]}

        # sound
        if notification.sound:
            hints["sound-name"] = Variant("s", "message-new-instant")

        # attachment
        if notification.attachment:
            hints["image-path"] = Variant("s", notification.attachment)

        # Post the new notification and record the platform ID assigned to it.
        platform_nid = await self.interface.call_notify(
            self.app_name,  # app_name
            replaces_nid,  # replaces_id
            notification.icon or "",  # app_icon
            notification.title,  # summary
            notification.message,  # body
            actions,  # actions
            hints,  # hints
            -1,  # expire_timeout (-1 = default)
        )

        return platform_nid

    def _clear(self, notification: Notification) -> None:
        """
        Synchronously removes a notifications from the notification center

        :param notification: Notification to clear.
        """
        self._run_coco_sync(self._clear_async(notification))

    async def _clear_async(self, notification: Notification) -> None:
        """
        Asynchronously removes a notification from the notification center
        """

        if not self.interface:
            return

        await self.interface.call_close_notification(notification.identifier)

    def _clear_all(self) -> None:
        """
        Synchronously clears all notifications from notification center

        The org.freedesktop.Notifications specification does not support retrieving or
        or clearing all notifications for an app name directly. We therefore rely on our
        cache of already delivered notifications and clear them individually. Since this
        is not persistent between Python sessions, notifications delivered in a previous
        session will not be cleared.
        """
        self._run_coco_sync(self._clear_all_async())

    async def _clear_all_async(self) -> None:
        """
        Asynchronously clears all notifications from notification center
        """

        if not self.interface:
            return

        for notification in self.current_notifications:
            await self.interface.call_close_notification(notification.identifier)

    # Note that _on_action and _on_closed might be called for the same notification
    # with some notification servers. This is not a problem because the _on_action
    # call will come first, in which case we are no longer interested in calling the
    # on_dismissed callback.

    def _on_action(self, nid, action_key) -> None:

        # Get the notification instance from the platform ID.
        nid = int(nid)
        action_key = str(action_key)
        notification = self._notification_for_nid.get(nid)

        # Execute any callbacks for button clicks.
        if notification:
            self._clear_notification_from_cache(notification)

            if action_key == "default" and notification.on_clicked:
                notification.on_clicked()
            else:
                callback = notification.buttons.get(action_key)

                if callback:
                    callback()

    def _on_closed(self, nid, reason) -> None:

        # Get the notification instance from the platform ID.
        nid = int(nid)
        reason = int(reason)
        notification = self._notification_for_nid.get(nid)

        # Execute callback for user dismissal.
        if notification:
            self._clear_notification_from_cache(notification)

            if reason == NOTIFICATION_CLOSED_DISMISSED and notification.on_dismissed:
                notification.on_dismissed()
