# -*- coding: utf-8 -*-
"""
This module defines base classes for desktop notifications. All platform implementations
must inherit from :class:`DesktopNotifierBase`.
"""

# system imports
import logging
from enum import Enum
from collections import deque
from typing import Optional, Dict, Callable, Union, Deque, List


logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    """Enumeration of notification levels

    The interpretation and visuals will depend on the platform.
    """

    Critical = "critical"
    """For critical errors."""

    Normal = "normal"
    """Default platform notification level."""

    Low = "low"
    """Low priority notification."""


class Notification:
    """A desktop notification

    :param title: Notification title.
    :param message: Notification message.
    :param urgency: Notification level: low, normal or critical. This is ignored by some
        implementations.
    :param icon: Path to an icon to use for the notification, typically the app icon.
        This is ignored by some implementations, e.g., on macOS where the icon of the
        app bundle is always used.
    :param action: Handler to call when the notification is clicked. This is ignored by
        some implementations.
    :param buttons: A dictionary with button names to show in the notification and
        handler to call when the respective button is clicked. This is ignored by some
        implementations.
    """

    def __init__(
        self,
        title: str,
        message: str,
        urgency: NotificationLevel = NotificationLevel.Normal,
        icon: Optional[str] = None,
        action: Optional[Callable] = None,
        buttons: Optional[Dict[str, Callable]] = None,
        sound: bool = False,
    ) -> None:

        self._identifier: Union[str, int, None] = None
        self.title = title
        self.message = message
        self.urgency = urgency
        self.icon = icon
        self.action = action
        self.buttons = buttons or dict()
        self.sound = sound

    @property
    def identifier(self) -> Union[str, int, None]:
        """
        An platform identifier which gets assigned to the notification after it was
        sent. This may be a str or int.
        """
        return self._identifier

    @identifier.setter
    def identifier(self, value: Union[str, int, None]) -> None:
        """Setter: identifier"""
        self._identifier = value

    def __repr__(self):
        return f"<{self.__class__.__name__}(title='{self.title}', message='{self.message}')>"


class DesktopNotifierBase:
    """Base class for desktop notifier implementations

    :param app_name: Name to identify the application in the notification center.
    :param app_icon: Default icon to use for notifications.
    :param notification_limit: Maximum number of notifications to keep in the system's
        notification center.
    """

    def __init__(
        self,
        app_name: str = "Python",
        app_icon: Optional[str] = None,
        notification_limit: Optional[int] = None,
    ) -> None:
        self.app_name = app_name
        self.app_icon = app_icon
        self.notification_limit = notification_limit
        self._current_notifications: Deque[Notification] = deque([], notification_limit)
        self._notification_for_nid: Dict[Union[str, int], Notification] = {}

    def send(self, notification: Notification) -> None:
        """
        Sends a desktop notification. Some arguments may be ignored, depending on the
        implementation. This is a wrapper method which mostly performs housekeeping of
        notifications ID and calls :meth:`_send` to actually schedule the notification.
        Platform implementations must implement :meth:`_send`.

        :param notification: Notification to send.
        """

        if not notification.icon:
            notification.icon = self.app_icon

        notification_to_replace: Optional[Notification]

        if len(self._current_notifications) == self.notification_limit:
            notification_to_replace = self._current_notifications.popleft()
        else:
            notification_to_replace = None

        try:
            platform_nid = self._send(notification, notification_to_replace)
        except Exception:
            # Notifications can fail for many reasons:
            # The dbus service may not be available, we might be in a headless session,
            # etc. Since notifications are not critical to an application, we only emit
            # a warning.
            if notification_to_replace:
                self._current_notifications.appendleft(notification_to_replace)
            logger.warning("Notification failed", exc_info=True)
        else:
            notification.identifier = platform_nid
            self._current_notifications.append(notification)
            self._notification_for_nid[platform_nid] = notification

    def _send(
        self,
        notification: Notification,
        notification_to_replace: Optional[Notification],
    ) -> Union[str, int]:
        """
        Method to send a notification via the platform. This should be implemented by
        subclasses.

        :param notification: Notification to send.
        :param notification_to_replace: Notification to replace, if any.
        :returns: The platform's ID for the scheduled notification.
        """
        raise NotImplementedError()

    @property
    def current_notifications(self) -> List[Notification]:
        """
        A list of all notifications which currently displayed in the notification center
        """
        return list(self._current_notifications)

    def clear(self, notification: Notification) -> None:
        """
        Removes the given notification from the notification center. This is a wrapper
        method which mostly performs housekeeping of notifications ID and calls
        :meth:`_clear` to actually clear the notification. Platform implementations
        must implement :meth:`_clear`.

        :param notification: Notification to clear.
        """

        if notification.identifier:
            self._clear(notification)
            self._current_notifications.remove(notification)
            self._notification_for_nid.pop(notification.identifier)

    def _clear(self, notification: Notification) -> None:
        """
        Removes the given notification from the notification center. Should be
        implemented by subclasses.

        :param notification: Notification to clear.
        """
        raise NotImplementedError()

    def clear_all(self) -> None:
        """
        Clears all notifications from the notification center. This is a wrapper method
        which mostly performs housekeeping of notifications ID and calls
        :meth:`_clear_all` to actually clear the notifications. Platform implementations
        must implement :meth:`_clear_all`.
        """

        self._clear_all()
        self._current_notifications.clear()
        self._notification_for_nid.clear()

    def _clear_all(self) -> None:
        """
        Clears all notifications from the notification center. Should be implemented by
        subclasses.
        """
        raise NotImplementedError()
