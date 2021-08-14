# -*- coding: utf-8 -*-
"""
This module defines base classes for desktop notifications. All platform implementations
must inherit from :class:`DesktopNotifierBase`.
"""

# system imports
import logging
from enum import Enum
from collections import deque
from typing import Optional, Dict, Callable, Any, Union, Deque, List, Sequence

try:
    from importlib.resources import path  # type: ignore
except ImportError:
    from importlib_resources import path  # type: ignore


logger = logging.getLogger(__name__)

PYTHON_ICON_PATH = path("desktop_notifier.resources", "python.png").__enter__()


class AuthorisationError(Exception):
    """Raised when we are not authorised to send notifications"""


class Urgency(Enum):
    """Enumeration of notification levels

    The interpretation and visuals will depend on the platform.
    """

    Critical = "critical"
    """For critical errors."""

    Normal = "normal"
    """Default platform notification level."""

    Low = "low"
    """Low priority notification."""


class Button:
    """
    A button for interactive notifications

    :param title: The button title.
    :param on_pressed: Callback to invoke when the button is pressed. This is called
        without any arguments.
    """

    def __init__(
        self, title: str, on_pressed: Optional[Callable[[], Any]] = None
    ) -> None:
        self.title = title
        self.on_pressed = on_pressed

    def __repr__(self):
        return f"<{self.__class__.__name__}(title='{self.title}', on_pressed={self.on_pressed})>"


class ReplyField:
    """
    A reply field for interactive notifications

    :param title: A title for the field itself. On macOS, this will be the title of a
        button to show the field.
    :param button_title: The title of the button to send the reply.
    :param on_replied: Callback to invoke when the button is pressed. This is called
        without any arguments.
    """

    def __init__(
        self,
        title: str = "Reply",
        button_title: str = "Send",
        on_replied: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self.title = title
        self.button_title = button_title
        self.on_replied = on_replied

    def __repr__(self):
        return f"<{self.__class__.__name__}(title='{self.title}', on_replied={self.on_replied})>"


class Notification:
    """A desktop notification

    :param title: Notification title.
    :param message: Notification message.
    :param urgency: Notification level: low, normal or critical.
    :param icon: URI for an icon to use for the notification or icon name.
    :param buttons: A list of buttons for the notification.
    :param reply_field: An optional reply field/
    :param on_clicked: Callback to call when the notification is clicked. The
        callback will be called without any arguments.
    :param on_dismissed: Callback to call when the notification is dismissed. The
        callback will be called without any arguments.
    :attachment: URI for an attachment to the notification.
    :param sound: Whether to play a sound when the notification is shown.
    :param thread: An identifier to group related notifications together.
    """

    def __init__(
        self,
        title: str,
        message: str,
        urgency: Urgency = Urgency.Normal,
        icon: Optional[str] = None,
        buttons: Sequence[Button] = (),
        reply_field: Optional[ReplyField] = None,
        on_clicked: Optional[Callable[[], Any]] = None,
        on_dismissed: Optional[Callable[[], Any]] = None,
        attachment: Optional[str] = None,
        sound: bool = False,
        thread: Optional[str] = None,
    ) -> None:

        self._identifier: Union[str, int, None] = None
        self.title = title
        self.message = message
        self.urgency = urgency
        self.icon = icon
        self.buttons = buttons
        self.reply_field = reply_field
        self.on_clicked = on_clicked
        self.on_dismissed = on_dismissed
        self.attachment = attachment
        self.sound = sound
        self.thread = thread

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

    async def request_authorisation(self) -> bool:
        """
        Request authorisation to send notifications.

        :returns: Whether authorisation has been granted.
        """
        raise NotImplementedError()

    async def has_authorisation(self) -> bool:
        """
        Returns whether we have authorisation to send notifications.
        """
        raise NotImplementedError()

    async def send(self, notification: Notification) -> None:
        """
        Sends a desktop notification. Some arguments may be ignored, depending on the
        implementation. This is a wrapper method which mostly performs housekeeping of
        notifications ID and calls :meth:`_send` to actually schedule the notification.
        Platform implementations must implement :meth:`_send`.

        :param notification: Notification to send.
        """

        notification_to_replace: Optional[Notification]

        if len(self._current_notifications) == self.notification_limit:
            notification_to_replace = self._current_notifications.popleft()
        else:
            notification_to_replace = None

        try:
            platform_nid = await self._send(notification, notification_to_replace)
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

    def _clear_notification_from_cache(self, notification: Notification) -> None:
        """
        Removes the notification from our cache. Should be called by backends when the
        notification is closed.
        """
        try:
            self._current_notifications.remove(notification)
        except ValueError:
            pass

        if notification.identifier:
            try:
                self._notification_for_nid.pop(notification.identifier)
            except KeyError:
                pass

    async def _send(
        self,
        notification: Notification,
        notification_to_replace: Optional[Notification],
    ) -> Union[str, int]:
        """
        Method to send a notification via the platform. This should be implemented by
        subclasses.

        Implementations must raise an exception when the notification could not be
        delivered. If the notification could be delivered but not fully as intended,
        e.g., because associated resources could not be loaded, implementations should
        emit a log message of level warning.

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

    async def clear(self, notification: Notification) -> None:
        """
        Removes the given notification from the notification center. This is a wrapper
        method which mostly performs housekeeping of notifications ID and calls
        :meth:`_clear` to actually clear the notification. Platform implementations
        must implement :meth:`_clear`.

        :param notification: Notification to clear.
        """

        if notification.identifier:
            await self._clear(notification)

        self._clear_notification_from_cache(notification)

    async def _clear(self, notification: Notification) -> None:
        """
        Removes the given notification from the notification center. Should be
        implemented by subclasses.

        :param notification: Notification to clear.
        """
        raise NotImplementedError()

    async def clear_all(self) -> None:
        """
        Clears all notifications from the notification center. This is a wrapper method
        which mostly performs housekeeping of notifications ID and calls
        :meth:`_clear_all` to actually clear the notifications. Platform implementations
        must implement :meth:`_clear_all`.
        """

        await self._clear_all()
        self._current_notifications.clear()
        self._notification_for_nid.clear()

    async def _clear_all(self) -> None:
        """
        Clears all notifications from the notification center. Should be implemented by
        subclasses.
        """
        raise NotImplementedError()
