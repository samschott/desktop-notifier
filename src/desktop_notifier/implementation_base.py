# -*- coding: utf-8 -*-
"""
This module defines the abstract implementation class that backends must inherit from.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from .base import Notification, Capability

__all__ = [
    "DesktopNotifierImplementation",
]


logger = logging.getLogger(__name__)


class DesktopNotifierImplementation(ABC):
    """Base class for desktop notifier implementations

    :param app_name: Name to identify the application in the notification center.
    """

    def __init__(self, app_name: str) -> None:
        self.app_name = app_name
        self._notification_cache: dict[str, Notification] = dict()

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

    def _clear_notification_from_cache(self, identifier: str) -> None:
        """
        Removes the notification from our cache. Should be called by backends when the
        notification is closed.
        """
        self._notification_cache.pop(identifier, None)

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

    @property
    def current_notifications(self) -> list[Notification]:
        """
        A list of all notifications which currently displayed in the notification center
        """
        return list(self._notification_cache.values())

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