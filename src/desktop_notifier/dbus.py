# -*- coding: utf-8 -*-
"""
Notification backend for Linux. Includes an implementation to send desktop notifications
over Dbus. Responding to user interaction with a notification requires a running asyncio
event loop.
"""

# system imports
import asyncio
import logging
from typing import Optional, Coroutine, TypeVar

# external imports
from dbus_next import Variant  # type: ignore
from dbus_next.aio import MessageBus, ProxyInterface  # type: ignore

# local imports
from .base import Notification, DesktopNotifierBase, NotificationLevel


__all__ = ["DBusDesktopNotifier"]

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DBusDesktopNotifier(DesktopNotifierBase):
    """DBus notification backend for Linux

    This implements the org.freedesktop.Notifications standard. The DBUS connection is
    created in a thread with a running asyncio loop to handle clicked notifications.

    :param app_name: The name of the app. If it matches the application name in an
        existing desktop entry, the icon from that entry will be used by default.
    :param notification_limit: Maximum number of notifications to keep in the system's
        notification center.
    """

    _to_native_urgency = {
        NotificationLevel.Low: Variant("y", 0),
        NotificationLevel.Normal: Variant("y", 1),
        NotificationLevel.Critical: Variant("y", 2),
    }

    def __init__(self, app_name: str = "Python", notification_limit: int = 5) -> None:
        super().__init__(app_name, notification_limit)
        self._loop = asyncio.get_event_loop()
        self.interface: Optional[ProxyInterface] = None
        self._did_attempt_connect = False

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

    async def _init_dbus(self) -> None:

        try:
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
            if hasattr(self.interface, "on_action_invoked"):
                # some older interfaces may not support notification actions
                self.interface.on_action_invoked(self._on_action)
        except Exception as exc:
            logger.warning("Could not connect to DBUS interface: %s", exc.args[0])
        finally:
            self._did_attempt_connect = True

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
        if not self._did_attempt_connect:
            await self._init_dbus()

        if not self.interface:
            raise RuntimeError("No DBus interface")

        if notification_to_replace:
            replaces_nid = notification_to_replace.identifier
        else:
            replaces_nid = 0

        # Create list of actions with default and user-supplied.
        actions = ["default", "default"]

        for button_name in notification.buttons.keys():
            actions += [button_name, button_name]

        # Post the new notification and record the platform ID assigned to it.
        platform_nid = await self.interface.call_notify(
            self.app_name,  # app_name
            replaces_nid,  # replaces_id
            notification.icon or "",  # app_icon
            notification.title,  # summary
            notification.message,  # body
            actions,  # actions
            {"urgency": self._to_native_urgency[notification.urgency]},  # hints
            -1,  # expire_timeout (-1 = default)
        )

        return platform_nid

    def _on_action(self, nid, action_key) -> None:

        # Get the notification instance from the platform ID.
        nid = int(nid)
        action_key = str(action_key)
        notification = next(
            iter(n for n in self.current_notifications.values() if n.identifier == nid),
            None,
        )

        # Execute any callbacks for button clicks.
        if notification:
            if action_key == "default" and notification.action:
                notification.action()
            else:
                callback = notification.buttons.get(action_key)

                if callback:
                    callback()
