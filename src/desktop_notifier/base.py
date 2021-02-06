# -*- coding: utf-8 -*-
"""
This module defines base classes for desktop notifications. All platform implementations
must inherit from :class:`DesktopNotifierBase`.
"""

# system imports
import logging
from enum import Enum
from typing import Optional, Dict, Callable, Union


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
    ) -> None:

        self._identifier: Union[str, int, None] = None
        self.title = title
        self.message = message
        self.urgency = urgency
        self.icon = icon
        self.action = action
        self.buttons = buttons or dict()

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
    :param notification_limit: Maximum number of notifications to keep in the system's
        notification center.
    """

    def __init__(self, app_name: str = "Python", notification_limit: int = 5) -> None:
        self.app_name = app_name
        self.notification_limit = notification_limit
        self._current_notifications: Dict[int, Notification] = dict()
        self._current_nid = notification_limit - 1

    def send(self, notification: Notification) -> None:
        """
        Sends a desktop notification. Some arguments may be ignored, depending on the
        implementation. This is a wrapper function which mostly performs housekeeping of
        notifications ID and uses :meth:`_send` to actually schedule the notification.
        Platform implementations should therefore override :meth:`_send`.

        :param notification: Notification to send.
        """

        internal_nid = self.next_nid()
        notification_to_replace = self.current_notifications.get(internal_nid)

        try:
            platform_nid = self._send(notification, notification_to_replace)
        except Exception:
            # Notifications can fail for many reasons:
            # The dbus service may not be available, we might be in a headless session,
            # etc. Since notifications are not critical to an application, we only emit
            # a warning.
            logger.warning("Notification failed", exc_info=True)
        else:
            notification.identifier = platform_nid
            self._current_notifications[internal_nid] = notification
            self._current_nid = internal_nid

    def _send(
        self,
        notification: Notification,
        notification_to_replace: Optional[Notification],
    ) -> Union[str, int, None]:
        """
        Method to send a notification via the platform. This should be implemented by
        subclasses.

        :returns: The platform's ID for the scheduled notification.
        """
        pass

    @property
    def current_nid(self) -> int:
        """
        The ID of the last notification which was sent. This ID is an integer between
        0 and ``notification_limit - 1``. This may differ from any internal ID assigned
        to the notification by the platform.
        """
        return self._current_nid

    @property
    def current_notifications(self) -> Dict[int, Notification]:
        """
        A dictionary of all notifications which are set to be displayed in the
        notification center. Keys are integer notification IDs.
        """
        return self._current_notifications

    def next_nid(self) -> int:
        """
        Returns the notification ID to be used for the next notification. This may
        return the ID of a notification which was already presented, when exceeding out
        :attr:`notification_limit`, in which case the old notification should be
        removed or replaced.
        """
        return (self.current_nid + 1) % self.notification_limit
