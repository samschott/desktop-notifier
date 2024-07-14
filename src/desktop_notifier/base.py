# -*- coding: utf-8 -*-
"""
This module defines base classes for desktop notifications. All platform implementations
must inherit from :class:`DesktopNotifierBase`.
"""
from __future__ import annotations

import logging
import uuid
import urllib.parse
import warnings
import dataclasses
from urllib.parse import urlparse, unquote
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum, auto
from pathlib import Path
from typing import (
    Callable,
    Any,
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


def uuid_str() -> str:
    return str(uuid.uuid4())


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


DEFAULT_ICON: Icon = Icon(path=python_icon_path)
"""Python icon"""

DEFAULT_SOUND: Sound = Sound(name="default")
"""Default system notification sound"""


class AuthorisationError(Exception):
    """Raised when we are not authorised to send notifications"""


class Urgency(Enum):
    """Enumeration of notification levels

    The interpretation and visuals depend on the platform.
    """

    Critical = "critical"
    """For critical errors."""

    Normal = "normal"
    """Default platform notification level."""

    Low = "low"
    """Low priority notification."""


@dataclass
class Button:
    """A button for interactive notifications"""

    title: str
    """The localized button title"""

    on_pressed: Callable[[], Any] | None = None
    """Method to call when the button is pressed"""

    identifier: str = dataclasses.field(default_factory=uuid_str)
    """A unique identifier to use in callbacks to specify with button was clicked"""


@dataclass
class ReplyField:
    """A text field for interactive notifications"""

    title: str = "Reply"
    """A title for the field itself. On macOS, this will be the title of a button to
    show the field."""

    button_title: str = "Send"
    """The title of the button to send the reply"""

    on_replied: Callable[[str], Any] | None = None
    """Method to call when the 'reply' button is pressed"""


class Notification:
    """A desktop notification

    Some properties of a notification may be ignored or interpreted differently
    depending on the platform.
    """

    title: str
    """Notification title"""

    message: str
    """Notification message"""

    urgency: Urgency
    """Notification urgency. Can determine stickiness, notification appearance and
    break through silencing."""

    icon: Icon | None
    """Icon to use for the notification"""

    buttons: tuple[Button, ...]
    """Buttons shown on an interactive notification"""

    reply_field: ReplyField | None
    """Text field shown on an interactive notification. This can be used for example
    for messaging apps to reply directly from the notification."""

    on_clicked: Callable[[], Any] | None
    """Method to call when the notification is clicked"""

    on_dismissed: Callable[[], Any] | None
    """Method to call when the notification is dismissed"""

    attachment: Attachment | None
    """A file attached to the notification which may be displayed as a preview"""

    sound: Sound | None
    """A sound to play on notification"""

    thread: str | None
    """An identifier to group related notifications together, e.g., from a chat space"""

    timeout: int = -1
    """Duration for which the notification is shown"""

    identifier: str
    """A unique identifier for this notification. Generated automatically if not
    passed by the client."""

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
        identifier: str | None = None,
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

        self.identifier = identifier or uuid_str()

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

    def _clear_notification_from_cache(self, notification: Notification) -> None:
        """
        Removes the notification from our cache. Should be called by backends when the
        notification is closed.
        """
        self._notification_cache.pop(notification.identifier, None)

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
    def current_notifications(self) -> List[Notification]:
        """
        A list of all notifications which currently displayed in the notification center
        """
        return list(self._notification_cache.values())

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
