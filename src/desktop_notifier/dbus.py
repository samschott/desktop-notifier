# -*- coding: utf-8 -*-
"""
Notification backend for Linux

Includes an implementation to send desktop notifications over Dbus. Responding to user
interaction with a notification requires a running asyncio event loop.
"""

from __future__ import annotations

# system imports
import logging
from typing import TypeVar

# external imports
from dbus_next.signature import Variant
from dbus_next.aio.message_bus import MessageBus
from dbus_next.aio.proxy_object import ProxyInterface

# local imports
from .base import Notification, DesktopNotifierBase, Urgency, Capability


__all__ = ["DBusDesktopNotifier"]

logger = logging.getLogger(__name__)

T = TypeVar("T")

NOTIFICATION_CLOSED_EXPIRED = 1
NOTIFICATION_CLOSED_DISMISSED = 2
NOTIFICATION_CLOSED_PROGRAMMATICALLY = 3
NOTIFICATION_CLOSED_UNDEFINED = 4


def identifier_from_dbus(nid: int) -> str:
    if nid == 0:
        return ""
    return str(nid)


def identifier_to_dbus(nid: str) -> int:
    if nid == "":
        return 0
    return int(nid)


class DBusDesktopNotifier(DesktopNotifierBase):
    """DBus notification backend for Linux

    This implements the org.freedesktop.Notifications standard. The DBUS connection is
    created in a thread with a running asyncio loop to handle clicked notifications.

    :param app_name: The name of the app. If it matches the application name in an
        existing desktop entry, the icon from that entry will be used by default.
    :param notification_limit: Maximum number of notifications to keep in the system's
        notification center.
    """

    to_native_urgency = {
        Urgency.Low: Variant("y", 0),
        Urgency.Normal: Variant("y", 1),
        Urgency.Critical: Variant("y", 2),
    }

    supported_hint_signatures = {"a{sv}", "a{ss}"}

    def __init__(
        self,
        app_name: str = "Python",
        notification_limit: int | None = None,
    ) -> None:
        super().__init__(app_name, notification_limit)
        self.interface: ProxyInterface | None = None

    async def request_authorisation(self) -> bool:
        """
        Request authorisation to send notifications.

        :returns: Whether authorisation has been granted.
        """
        return True

    async def has_authorisation(self) -> bool:
        """
        Whether we have authorisation to send notifications.
        """
        return True

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

    async def _send(
        self,
        notification: Notification,
        notification_to_replace: Notification | None,
    ) -> None:
        """
        Asynchronously sends a notification via the Dbus interface.

        :param notification: Notification to send.
        :param notification_to_replace: Notification to replace, if any.
        """
        if not self.interface:
            self.interface = await self._init_dbus()

        if notification_to_replace:
            replaces_nid = identifier_to_dbus(notification_to_replace.identifier)
        else:
            replaces_nid = 0

        actions: list[str] = []

        if notification.on_clicked:
            # The "default" action is typically invoked when clicking on the
            # notification body itself, see
            # https://specifications.freedesktop.org/notification-spec. There are some
            # exceptions though, such as XFCE, where this will result in a separate
            # button. If no label name is provided in XFCE, it will result in a default
            # symbol being used. We therefore don't specify a label name.
            actions = ["default", ""]

        for n, button in enumerate(notification.buttons):
            actions += [str(n), button.title]

        hints_v: dict[str, Variant] = dict()
        hints_v["urgency"] = self.to_native_urgency[notification.urgency]

        if notification.sound:
            if notification.sound.is_named():
                hints_v["sound-name"] = Variant("s", "message-new-instant")
            else:
                hints_v["sound-file"] = Variant("s", notification.sound.as_uri())

        if notification.attachment:
            hints_v["image-path"] = Variant("s", notification.attachment.as_uri())

        # The current notification spec defines hints as a Dbus dictionary type 'a{sv}',
        # represented in Python as dict[str, Variant]. However, some older notification
        # servers expect 'a{ss}' (Python dict[str, str]). We therefore check the
        # expected argument type at runtime and cast arguments accordingly.
        # See https://github.com/samschott/desktop-notifier/issues/143.
        hints_signature = get_hints_signature(self.interface)

        if hints_signature == "":
            logger.warning("Notification server not supported")
            return

        hints: dict[str, str] | dict[str, Variant]

        if hints_signature == "a{sv}":
            hints = hints_v
        elif hints_signature == "a{ss}":
            hints = {k: str(v.value) for k, v in hints_v.items()}
        else:
            hints = {}

        timeout = notification.timeout * 1000 if notification.timeout != -1 else -1
        if notification.icon:
            if notification.icon.is_named():
                icon = notification.icon.name
            else:
                icon = notification.icon.as_uri()
        else:
            icon = ""

        # dbus_next proxy APIs are generated at runtime. Silence the type checker but
        # raise an AttributeError if required.
        platform_nid = await self.interface.call_notify(  # type:ignore[attr-defined]
            self.app_name,
            replaces_nid,
            icon,
            notification.title,
            notification.message,
            actions,
            hints,
            timeout,
        )

        notification.identifier = identifier_from_dbus(platform_nid)

    async def _clear(self, notification: Notification) -> None:
        """
        Asynchronously removes a notification from the notification center
        """
        if not self.interface:
            return

        # dbus_next proxy APIs are generated at runtime. Silence the type checker but
        # raise an AttributeError if required.
        await self.interface.call_close_notification(  # type:ignore[attr-defined]
            identifier_to_dbus(notification.identifier)
        )

    async def _clear_all(self) -> None:
        """
        Asynchronously clears all notifications from notification center
        """
        if not self.interface:
            return

        for notification in self.current_notifications:
            # dbus_next proxy APIs are generated at runtime. Silence the type checker
            # but raise an AttributeError if required.
            await self.interface.call_close_notification(  # type:ignore[attr-defined]
                identifier_to_dbus(notification.identifier)
            )

    # Note that _on_action and _on_closed might be called for the same notification
    # with some notification servers. This is not a problem because the _on_action
    # call will come first, in which case we are no longer interested in calling the
    # _on_closed callback.

    def _on_action(self, nid: int, action_key: str) -> None:
        """
        Called when the user performs a notification action. This will invoke the
        handler callback.

        :param nid: The platform's notification ID as an integer.
        :param action_key: A string identifying the action to take. We choose those keys
            ourselves when scheduling the notification.
        """
        notification = self._notification_for_nid.get(identifier_from_dbus(nid))

        if notification:
            self._clear_notification_from_cache(notification)

            button_number: int | None

            try:
                button_number = int(action_key)
            except ValueError:
                button_number = None

            if action_key == "default" and notification.on_clicked:
                notification.on_clicked()

            elif button_number is not None:
                button = notification.buttons[button_number]

                if button.on_pressed:
                    button.on_pressed()

    def _on_closed(self, nid: int, reason: int) -> None:
        """
        Called when the user closes a notification. This will invoke the registered
        callback.

        :param nid: The platform's notification ID as an integer.
        :param reason: An integer describing the reason why the notification was closed.
        """
        notification = self._notification_for_nid.get(identifier_from_dbus(nid))

        if notification:
            self._clear_notification_from_cache(notification)

            if reason == NOTIFICATION_CLOSED_DISMISSED and notification.on_dismissed:
                notification.on_dismissed()

    async def get_capabilities(self) -> frozenset[Capability]:
        if not self.interface:
            self.interface = await self._init_dbus()

        capabilities = {
            Capability.APP_NAME,
            Capability.ICON,
            Capability.TITLE,
            Capability.TIMEOUT,
            Capability.URGENCY,
        }

        # Capabilities supported by some notification servers.
        # See https://specifications.freedesktop.org/notification-spec/notification-spec-latest.html#protocol.
        if hasattr(self.interface, "on_notification_closed"):
            capabilities.add(Capability.ON_CLICKED)
            capabilities.add(Capability.ON_DISMISSED)

        cps = await self.interface.call_get_capabilities()  # type:ignore[attr-defined]
        if "actions" in cps:
            capabilities.add(Capability.BUTTONS)
        if "body" in cps:
            capabilities.add(Capability.MESSAGE)
        if "sound" in cps:
            capabilities.add(Capability.SOUND)
            capabilities.add(Capability.SOUND_NAME)

        hints_signature = get_hints_signature(self.interface)
        if hints_signature not in self.supported_hint_signatures:
            # Any hint-based capabilities are not supported because we got an unexpected
            # DBus interface.
            capabilities.discard(Capability.SOUND)
            capabilities.discard(Capability.SOUND_NAME)
            capabilities.discard(Capability.URGENCY)

        return frozenset(capabilities)


def get_hints_signature(interface: ProxyInterface) -> str:
    """Returns the dbus type signature for the hints argument"""
    methods = interface.introspection.methods
    notify_method = next(m for m in methods if m.name == "Notify")
    try:
        return str(notify_method.in_args[6].signature)
    except IndexError:
        return ""
