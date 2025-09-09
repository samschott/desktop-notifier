# -*- coding: utf-8 -*-
"""
Notification backend for Linux

Includes an implementation to send desktop notifications over Dbus. Responding to user
interaction with a notification requires a running asyncio event loop.
"""
from __future__ import annotations

import os
import logging

import aiosqlite

from typing import TypeVar

from dbus_fast.aio.message_bus import MessageBus
from dbus_fast.aio.proxy_object import ProxyInterface
from dbus_fast.errors import DBusError
from dbus_fast.signature import Variant

from ..common import Capability, Icon, Notification, Urgency
from .base import DesktopNotifierBackend

__all__ = ["DBusDesktopNotifier"]

logger = logging.getLogger(__name__)

T = TypeVar("T")

NOTIFICATION_CLOSED_EXPIRED = 1
NOTIFICATION_CLOSED_DISMISSED = 2
NOTIFICATION_CLOSED_PROGRAMMATICALLY = 3
NOTIFICATION_CLOSED_UNDEFINED = 4

DEFAULT_ACTION_KEY = "default"
INLINE_REPLY_ACTION_KEY = "inline-reply"
INLINE_REPLY_BUTTON_TEXT_KEY = "x-kde-reply-submit-button-text"


def get_data_path() -> str:
    """
    Returns the default path to save application data for the platform. This will be
    "$XDG_DATA_DIR/SUBFOLDER/FILENAME" or "$HOME/.local/share/SUBFOLDER/FILENAME" if
    $XDG_DATA_DIR is not specified.
    """
    home_dir = os.path.expanduser("~")
    fallback = os.path.join(home_dir, ".local", "share")
    return os.environ.get("XDG_DATA_HOME", fallback)


def get_notification_index_path() -> str:
    data_path = get_data_path()
    db_directory = os.path.join(data_path, "desktop_notifier")
    os.makedirs(db_directory, exist_ok=True)
    return os.path.join(db_directory, "notification_index.db")


NOTIFICATION_INDEX_PATH = get_notification_index_path()


class DBusDesktopNotifier(DesktopNotifierBackend):
    """DBus notification backend for Linux

    This implements the org.freedesktop.Notifications standard. The DBUS connection is
    created in a thread with a running asyncio loop to handle clicked notifications.

    :param app_name: The name of the app.
    """

    to_native_urgency = {
        Urgency.Low: Variant("y", 0),
        Urgency.Normal: Variant("y", 1),
        Urgency.Critical: Variant("y", 2),
    }

    supported_hint_signatures = {"a{sv}", "a{ss}"}

    def __init__(self, app_name: str, app_icon: Icon | None = None) -> None:
        super().__init__(app_name, app_icon)
        self._interface: ProxyInterface | None = None
        self._notification_index: aiosqlite.Connection | None = None

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

    async def _get_interface(self) -> ProxyInterface:
        if not self._interface:
            self._interface = await self._init_dbus()
        return self._interface

    async def _get_notification_index(self) -> aiosqlite.Connection:
        if not self._notification_index:
            self._notification_index = await self._init_index()
        return self._notification_index

    async def _init_dbus(self) -> ProxyInterface:
        bus = await MessageBus().connect()
        introspection = await bus.introspect(
            "org.freedesktop.Notifications", "/org/freedesktop/Notifications"
        )
        proxy_object = bus.get_proxy_object(
            "org.freedesktop.Notifications",
            "/org/freedesktop/Notifications",
            introspection,
        )
        interface = proxy_object.get_interface("org.freedesktop.Notifications")

        # Some older interfaces may not support notification actions.
        if hasattr(interface, "on_notification_closed"):
            interface.on_notification_closed(self._on_closed)

        if hasattr(interface, "on_action_invoked"):
            interface.on_action_invoked(self._on_action)

        if hasattr(interface, "on_notification_replied"):
            interface.on_notification_replied(self._on_reply)

        return interface

    async def _init_index(self) -> aiosqlite.Connection:
        notification_index = await aiosqlite.connect(NOTIFICATION_INDEX_PATH)
        await notification_index.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_index(
              desktop_notifier_id STRING PRIMARY KEY, dbus_server_id INTEGER
            )
            """
        )

        return notification_index

    async def _store_platform_id(self, identifier: str, platform_id: int) -> None:
        index = await self._get_notification_index()
        await index.execute(
            "INSERT INTO notification_index (desktop_notifier_id,dbus_server_id) VALUES (?,?)",
            (identifier, platform_id),
        )

    async def _pop_platform_id(self, identifier: str) -> int:
        index = await self._get_notification_index()
        cur = await index.execute(
            "SELECT dbus_server_id FROM notification_index WHERE desktop_notifier_id = ?",
            identifier,
        )

        result = await cur.fetchone()

        if result is None:
            raise KeyError(f"Notification with identifier {identifier} not known")

        await index.execute(
            "DELETE FROM notification_index WHERE desktop_notifier_id = ?",
            identifier,
        )

        return result[0]

    async def _pop_identifier(self, platform_id: int) -> str:
        index = await self._get_notification_index()
        cur = await index.execute(
            "SELECT desktop_notifier_id FROM notification_index WHERE dbus_server_id = ?",
            platform_id,
        )
        result = cur.fetchone()

        if result is None:
            raise KeyError(f"Notification with platform id {platform_id} not known")

        await index.execute(
            "DELETE FROM notification_index WHERE dbus_server_id = ?",
            platform_id,
        )

        return result[0]

    async def _send(self, notification: Notification) -> None:
        """
        Asynchronously sends a notification via the Dbus interface.

        :param notification: Notification to send.
        """
        interface = await self._get_interface()

        actions = []
        hints_v: dict[str, Variant] = dict()

        # The "default" action is invoked when clicking on the notification body.
        if Capability.ON_CLICKED in await self.get_capabilities():
            actions += [DEFAULT_ACTION_KEY, ""]

        for button in notification.buttons:
            actions += [button.identifier, button.title]

        if (
            notification.reply_field
            and Capability.REPLY_FIELD in await self.get_capabilities()
        ):
            actions += [INLINE_REPLY_ACTION_KEY, notification.reply_field.title]
            hints_v[INLINE_REPLY_BUTTON_TEXT_KEY] = Variant(
                "s", notification.reply_field.button_title
            )

        hints_v["urgency"] = self.to_native_urgency[notification.urgency]

        if notification.sound:
            if notification.sound.is_named():
                hints_v["sound-name"] = Variant("s", notification.sound.name)
            else:
                hints_v["sound-file"] = Variant("s", notification.sound.as_uri())

        if notification.attachment:
            hints_v["image-path"] = Variant("s", notification.attachment.as_uri())

        # The current notification spec defines hints as a Dbus dictionary type 'a{sv}',
        # represented in Python as dict[str, Variant]. However, some older notification
        # servers expect 'a{ss}' (Python dict[str, str]). We therefore check the
        # expected argument type at runtime and cast arguments accordingly.
        # See https://github.com/samschott/desktop-notifier/issues/143.
        hints_signature = get_hints_signature(interface)

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

        icon: str = ""
        if notification.icon:
            icon = (
                notification.icon.as_name()
                if notification.icon.is_named()
                else notification.icon.as_uri()
            )
        elif self.app_icon:
            icon = (
                self.app_icon.as_name()
                if self.app_icon.is_named()
                else self.app_icon.as_uri()
            )

        # dbus_next proxy APIs are generated at runtime. Silence the type checker but
        # raise an AttributeError if required.
        platform_id = await interface.call_notify(  # type:ignore[attr-defined]
            self.app_name,
            0,
            icon,
            notification.title,
            notification.message,
            actions,
            hints,
            timeout,
        )

        await self._store_platform_id(notification.identifier, platform_id)

    async def _clear(self, identifier: str) -> None:
        """
        Asynchronously removes a notification from the notification center
        """
        platform_id = await self._pop_platform_id(identifier)
        interface = self._get_interface()

        try:
            # dbus_next proxy APIs are generated at runtime. Silence the type checker
            # but raise an AttributeError if required.
            await interface.call_close_notification(  # type:ignore[attr-defined]
                platform_id
            )
        except DBusError:
            # Notification was already closed.
            # See https://specifications.freedesktop.org/notification-spec/latest/protocol.html#command-close-notification
            pass

    async def _clear_all(self) -> None:
        """
        Asynchronously clears all notifications from notification center
        """
        index = await self._get_notification_index()
        rows = await index.execute_fetchall(
            "SELECT dbus_server_id FROM notification_index"
        )
        identifiers = [row[0] for row in rows]

        for identifier in identifiers:
            await self._clear(identifier)

    # Note that _on_action and _on_closed might be called for the same notification
    # with some notification servers. This is not a problem because the _on_action
    # call will come first, in which case we are no longer interested in calling the
    # _on_closed callback.

    async def _on_action(self, nid: int, action_key: str) -> None:
        """
        Called when the user performs a notification action. This will invoke the
        handler callback.

        :param nid: The platform's notification ID as an integer.
        :param action_key: A string identifying the action to take. We choose those keys
            ourselves when scheduling the notification.
        """
        identifier = await self._pop_identifier(nid)

        if action_key == DEFAULT_ACTION_KEY:
            self.handle_clicked(identifier)
            return

        self.handle_button(identifier, action_key)

    async def _on_reply(self, nid: int, reply_text: str) -> None:
        """
        Called when the user replies to the notification. This will invoke the
        handler callback.

        :param nid: The platform's notification ID as an integer.
        :param reply_text: The text of the user's reply.
        """
        identifier = await self._pop_identifier(nid)
        self.handle_replied(identifier, reply_text)

    async def _on_closed(self, nid: int, reason: int) -> None:
        """
        Called when the user closes a notification. This will invoke the registered
        callback.

        :param nid: The platform's notification ID as an integer.
        :param reason: An integer describing the reason why the notification was closed.
        """
        identifier = await self._pop_identifier(nid)

        if reason == NOTIFICATION_CLOSED_DISMISSED:
            self.handle_dismissed(identifier)

    async def _get_capabilities(self) -> frozenset[Capability]:
        interface = await self._get_interface()

        capabilities = {
            Capability.APP_NAME,
            Capability.ICON,
            Capability.TITLE,
            Capability.TIMEOUT,
            Capability.URGENCY,
            Capability.ON_DISPATCHED,
        }

        # Capabilities supported by some notification servers.
        # See https://specifications.freedesktop.org/notification-spec/notification-spec-latest.html#protocol.
        if hasattr(interface, "on_notification_closed"):
            capabilities.add(Capability.ON_DISMISSED)

        server_info = (
            await interface.call_get_server_information()  # type:ignore[attr-defined]
        )

        # xfce4-notifyd does not support a "default" action when the notification is
        # clicked. See https://docs.xfce.org/apps/xfce4-notifyd/spec.
        if server_info[0] != "Xfce Notify Daemon":
            capabilities.add(Capability.ON_CLICKED)

        cps = await interface.call_get_capabilities()  # type:ignore[attr-defined]

        if "actions" in cps:
            capabilities.add(Capability.BUTTONS)
        if "body" in cps:
            capabilities.add(Capability.MESSAGE)
        if "sound" in cps:
            capabilities.add(Capability.SOUND)
            capabilities.add(Capability.SOUND_NAME)
        if "inline-reply" in cps:
            capabilities.add(Capability.REPLY_FIELD)

        hints_signature = get_hints_signature(interface)
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
