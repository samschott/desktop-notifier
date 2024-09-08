# -*- coding: utf-8 -*-
"""
This module defines the abstract implementation class that backends must inherit from.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable

from ..common import Capability, Notification

__all__ = [
    "DesktopNotifierBackend",
]


logger = logging.getLogger(__name__)


class DesktopNotifierBackend(ABC):
    """Base class for desktop notifier implementations

    :param app_name: Name to identify the application in the notification center.
    """

    def __init__(self, app_name: str) -> None:
        self.app_name = app_name
        self._notification_cache: dict[str, Notification] = dict()

        self.on_clicked: Callable[[str], Any] | None = None
        self.on_dismissed: Callable[[str], Any] | None = None
        self.on_button_pressed: Callable[[str, str], Any] | None = None
        self.on_replied: Callable[[str, str], Any] | None = None

    @abstractmethod
    async def request_authorisation(self) -> bool:
        """
        Request authorisation to send notifications.

        :returns: Whether authorisation has been granted.
        """
        ...

    @abstractmethod
    async def has_authorisation(self) -> bool:
        """
        Returns whether we have authorisation to send notifications.
        """
        ...

    async def send(self, notification: Notification) -> None:
        """
        Sends a desktop notification.

        :param notification: Notification to send.
        """
        try:
            await self._send(notification)
        except Exception:
            # Notifications can fail for many reasons:
            # The dbus service may not be available, we might be in a headless session,
            # etc. Since notifications are not critical to an application, we only emit
            # a warning.
            logger.warning("Notification failed", exc_info=True)
        else:
            logger.debug("Notification sent: %s", notification)
            self._notification_cache[notification.identifier] = notification

    def _clear_notification_from_cache(self, identifier: str) -> Notification | None:
        """
        Removes the notification from our cache. Should be called by backends when the
        notification is closed.
        """
        return self._notification_cache.pop(identifier, None)

    @abstractmethod
    async def _send(self, notification: Notification) -> None:
        """
        Method to send a notification via the platform. This should be implemented by
        subclasses.

        Implementations must raise an exception when the notification could not be
        delivered. If the notification could be delivered but not fully as intended,
        e.g., because associated resources could not be loaded, implementations should
        emit a log message of level warning.

        :param notification: Notification to send.
        """
        ...

    async def get_current_notifications(self) -> list[str]:
        """Returns identifiers of all currently displayed notifications for this app."""
        return list(self._notification_cache.keys())

    async def clear(self, identifier: str) -> None:
        """
        Removes the given notification from the notification center. This is a wrapper
        method which mostly performs housekeeping of notifications ID and calls
        :meth:`_clear` to actually clear the notification. Platform implementations
        must implement :meth:`_clear`.

        :param identifier: Notification identifier.
        """
        await self._clear(identifier)
        self._clear_notification_from_cache(identifier)

    @abstractmethod
    async def _clear(self, identifier: str) -> None:
        """
        Removes the given notification from the notification center. Should be
        implemented by subclasses.

        :param identifier: Notification identifier.
        """
        ...

    async def clear_all(self) -> None:
        """
        Clears all notifications from the notification center. This is a wrapper method
        which mostly performs housekeeping of notifications ID and calls
        :meth:`_clear_all` to actually clear the notifications. Platform implementations
        must implement :meth:`_clear_all`.
        """

        await self._clear_all()
        self._notification_cache.clear()

    @abstractmethod
    async def _clear_all(self) -> None:
        """
        Clears all notifications from the notification center. Should be implemented by
        subclasses.
        """
        ...

    @abstractmethod
    async def get_capabilities(self) -> frozenset[Capability]:
        """
        Returns the functionality supported by the implementation and, for Linux / dbus,
        the notification server.
        """
        ...

    def handle_clicked(
        self, identifier: str, notification: Notification | None = None
    ) -> None:
        if notification and notification.on_clicked:
            notification.on_clicked()
        elif self.on_clicked:
            self.on_clicked(identifier)

    def handle_dismissed(
        self, identifier: str, notification: Notification | None = None
    ) -> None:
        if notification and notification.on_dismissed:
            notification.on_dismissed()
        elif self.on_dismissed:
            self.on_dismissed(identifier)

    def handle_replied(
        self, identifier: str, reply_text: str, notification: Notification | None = None
    ) -> None:
        if (
            notification
            and notification.reply_field
            and notification.reply_field.on_replied
        ):
            notification.reply_field.on_replied(reply_text)
        elif self.on_replied:
            self.on_replied(identifier, reply_text)

    def handle_button(
        self,
        identifier: str,
        button_identifier: str,
        notification: Notification | None = None,
    ) -> None:
        if notification and button_identifier in notification._buttons_dict:
            button = notification._buttons_dict[button_identifier]
        else:
            button = None

        if button and button.on_pressed:
            button.on_pressed()
        elif self.on_button_pressed:
            self.on_button_pressed(identifier, button_identifier)
