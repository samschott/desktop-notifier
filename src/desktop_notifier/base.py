# -*- coding: utf-8 -*-
"""
This module defines base classes for desktop notifications. All platform implementations
must inherit from :class:`DesktopNotifierBase`.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse, unquote
import urllib.parse
import warnings
import dataclasses
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum, auto
from collections import deque
from pathlib import Path
from typing import (
    Dict,
    Callable,
    Any,
    Deque,
    List,
    Sequence,
    ContextManager,
)

__all__ = [
    "Capability",
    "FileResource",
    "Resource",
    "Icon",
    "Sound",
    "Attachment",
    "Button",
    "ReplyField",
    "Urgency",
    "AuthorisationError",
    "Notification",
    "DesktopNotifierBase",
    "DEFAULT_ICON",
    "DEFAULT_SOUND",
]

try:
    from importlib.resources import as_file, files

    def resource_path(package: str, resource: str) -> ContextManager[Path]:
        return as_file(files(package) / resource)

except ImportError:
    from importlib.resources import path as resource_path


logger = logging.getLogger(__name__)

python_icon_path = resource_path(
    package="desktop_notifier.resources", resource="python.png"
).__enter__()


@dataclass(frozen=True)
class FileResource:
    """
    A file resource represented by a URI or path

    Only one of :attr:`path` or :attr:`uri` can be set.
    """

    path: Path | None = None
    """Path to a local file"""

    uri: str | None = None
    """URI reference to a file"""

    def __post_init__(self) -> None:
        fields = dataclasses.fields(self)
        set_fields = [f for f in fields if getattr(self, f.name) != f.default]
        if len(set_fields) > 1:
            raise RuntimeError("Only a single field can be set")
        if len(set_fields) == 0:
            field_names = [f.name for f in fields]
            raise RuntimeError(f"Either of {field_names} must be set")

    def as_uri(self) -> str:
        """
        Returns the represented resource as a URI string
        """
        if self.uri is not None:
            return self.uri
        if self.path is not None:
            return self.path.as_uri()
        raise AttributeError("No path or URI provided")

    def as_path(self) -> Path:
        """
        Returns the represented resource as a Path

        Note that any information about the URI scheme is lost on conversion.
        """
        if self.path is not None:
            return self.path
        if self.uri is not None:
            parsed_uri = urlparse(self.uri)
            return Path(unquote(parsed_uri.path))

        raise AttributeError("No path or URI provided")


@dataclass(frozen=True)
class Resource(FileResource):
    """
    A resource represented by a resource name, URI or path

    Only one of :attr:`path`, :attr:`uri` or :attr:`name` can be set.
    """

    name: str | None = None
    """Name of the system resource"""

    def is_named(self) -> bool:
        """Returns whether the instance was initialized with ``name``"""
        return self.name is not None

    def is_file(self) -> bool:
        """Returns whether the instance was initialized with ``path`` or ``uri``"""
        return self.path is not None or self.uri is not None


@dataclass(frozen=True)
class Icon(Resource):
    """An icon represented by an icon name, URI or path"""

    pass


@dataclass(frozen=True)
class Attachment(FileResource):
    """An attachment represented by a URI or path"""

    pass


@dataclass(frozen=True)
class Sound(Resource):
    """A sound represented by a sound name, URI or path"""

    pass


DEFAULT_ICON = Icon(path=python_icon_path)
"""Python icon"""

DEFAULT_SOUND = Sound(name="default")
"""Default system notification sound"""


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
        self,
        title: str,
        on_pressed: Callable[[], Any] | None = None,
    ) -> None:
        self.title = title
        self.on_pressed = on_pressed

    def __repr__(self) -> str:
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
        on_replied: Callable[[str], Any] | None = None,
    ) -> None:
        self.title = title
        self.button_title = button_title
        self.on_replied = on_replied

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(title='{self.title}', on_replied={self.on_replied})>"


class Notification:
    """A desktop notification

    Some arguments may be ignored, depending on the backend.

    :param title: Notification title.
    :param message: Notification message.
    :param urgency: Notification level: low, normal or critical.
    :param icon: Icon to use for the notification.
    :param buttons: A list of buttons for the notification.
    :param reply_field: An optional reply field/
    :param on_clicked: Callback to call when the notification is clicked. The
        callback will be called without any arguments.
    :param on_dismissed: Callback to call when the notification is dismissed. The
        callback will be called without any arguments.
    :param attachment: URI for an attachment to the notification.
    :param sound: Sound to use for the notification. Use DEFAULT_SOUND for the
        platform's default notification sound.
    :param thread: An identifier to group related notifications together.
    :param timeout: Duration for which the notification in shown.
    """

    def __init__(
        self,
        title: str,
        message: str,
        urgency: Urgency = Urgency.Normal,
        icon: str | Icon | None = None,
        buttons: Sequence[Button] = (),
        reply_field: ReplyField | None = None,
        on_clicked: Callable[[], Any] | None = None,
        on_dismissed: Callable[[], Any] | None = None,
        attachment: str | Attachment | None = None,
        sound: bool | Sound | None = False,
        thread: str | None = None,
        timeout: int = -1,
    ) -> None:
        if sound is True:
            warnings.warn(
                message="Use sound=DEFAULT_SOUND instead of sound=True. "
                "Support for boolean input will be removed in a future release.",
                category=DeprecationWarning,
            )
            sound = DEFAULT_SOUND
        if sound is False:
            warnings.warn(
                message="Use sound=None instead of sound=False. "
                "Support for boolean input will be removed in a future release.",
                category=DeprecationWarning,
            )
            sound = None
        if isinstance(icon, str):
            warnings.warn(
                message="Pass an Icon instance instead of a string. "
                "Support for string input will be removed in a future release.",
                category=DeprecationWarning,
            )
            if urllib.parse.urlparse(icon).hostname != "":
                icon = Icon(uri=icon)
            else:
                icon = Icon(name=icon)
        if isinstance(attachment, str):
            warnings.warn(
                message="Pass an Attachment instance instead of a string. "
                "Support for string input will be removed in a future release.",
                category=DeprecationWarning,
            )
            attachment = Attachment(uri=attachment)

        self._identifier = ""
        self._winrt_identifier = ""
        self._macos_identifier = ""
        self._dbus_identifier = 0

        self.title = title
        self.message = message
        self.urgency = urgency
        self.icon = icon
        self.buttons = tuple(buttons)
        self.reply_field = reply_field
        self.sound = sound
        self.on_clicked = on_clicked
        self.on_dismissed = on_dismissed
        self.attachment = attachment
        self.thread = thread
        self.timeout = timeout

    @property
    def identifier(self) -> str:
        """Unique identifier for this notification

        Populated by the platform after scheduling the notification.
        """
        return self._identifier

    @identifier.setter
    def identifier(self, nid: str) -> None:
        self._identifier = nid

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}(identifier='{self.identifier}', "
            f"title='{self.title}', message='{self.message}')>"
        )


class Capability(Enum):
    """Notification capabilities that can be supported by a platform"""

    APP_NAME = auto()
    """Supports setting a custom app name"""

    TITLE = auto()
    """Supports setting a notification title"""

    MESSAGE = auto()
    """Supports setting a notification message"""

    URGENCY = auto()
    """Supports different urgency levels"""

    ICON = auto()
    """Supports custom notification icons"""

    ICON_FILE = auto()
    """Supports setting a custom icon from a user-provided file"""

    ICON_NAME = auto()
    """Supports setting a named system icon as notification icon"""

    BUTTONS = auto()
    """Supports at least two notification buttons"""

    REPLY_FIELD = auto()
    """Supports reply fields"""

    ATTACHMENT = auto()
    """Supports notification attachments. Allowed file types vary by platform."""

    ON_CLICKED = auto()
    """Supports on-clicked callbacks"""

    ON_DISMISSED = auto()
    """Supports on-dismissed callbacks"""

    SOUND = auto()
    """Supports custom notification sounds"""

    SOUND_FILE = auto()
    """Supports setting a custom sound from a user-provided file"""

    SOUND_NAME = auto()
    """Supports setting a named system sound as notification sound"""

    THREAD = auto()
    """Supports grouping notifications by topic thread"""

    TIMEOUT = auto()
    """Supports notification timeouts"""


class DesktopNotifierBase(ABC):
    """Base class for desktop notifier implementations

    :param app_name: Name to identify the application in the notification center.
    :param notification_limit: Maximum number of notifications to keep in the system's
        notification center.
    """

    def __init__(
        self,
        app_name: str = "Python",
        notification_limit: int | None = None,
    ) -> None:
        self.app_name = app_name
        self.notification_limit = notification_limit
        self._current_notifications: Deque[Notification] = deque([], notification_limit)
        self._notification_for_nid: Dict[str, Notification] = {}

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
        Sends a desktop notification. Some arguments may be ignored, depending on the
        implementation. This is a wrapper method which mostly performs housekeeping of
        notifications ID and calls :meth:`_send` to actually schedule the notification.
        Platform implementations must implement :meth:`_send`.

        :param notification: Notification to send.
        """
        notification_to_replace: Notification | None

        if len(self._current_notifications) == self.notification_limit:
            notification_to_replace = self._current_notifications.popleft()
        else:
            notification_to_replace = None

        try:
            await self._send(notification, notification_to_replace)
        except Exception:
            # Notifications can fail for many reasons:
            # The dbus service may not be available, we might be in a headless session,
            # etc. Since notifications are not critical to an application, we only emit
            # a warning.
            if notification_to_replace:
                self._current_notifications.appendleft(notification_to_replace)
            logger.warning("Notification failed", exc_info=True)
        else:
            self._current_notifications.append(notification)
            self._notification_for_nid[notification.identifier] = notification

    def _clear_notification_from_cache(self, notification: Notification) -> None:
        """
        Removes the notification from our cache. Should be called by backends when the
        notification is closed.
        """
        try:
            self._current_notifications.remove(notification)
        except ValueError:
            pass

        try:
            self._notification_for_nid.pop(notification.identifier)
        except KeyError:
            pass

    @abstractmethod
    async def _send(
        self,
        notification: Notification,
        notification_to_replace: Notification | None,
    ) -> None:
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
        ...

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

    @abstractmethod
    async def _clear(self, notification: Notification) -> None:
        """
        Removes the given notification from the notification center. Should be
        implemented by subclasses.

        :param notification: Notification to clear.
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
        self._current_notifications.clear()
        self._notification_for_nid.clear()

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
