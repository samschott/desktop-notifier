"""
This module defines base classes for desktop notifications.
"""

from __future__ import annotations

import dataclasses
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from immutabledict import immutabledict

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
    "DEFAULT_ICON",
    "DEFAULT_SOUND",
]


logger = logging.getLogger(__name__)
python_icon_path = as_file(
    files("desktop_notifier.resources") / "python.png"
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

    def as_name(self) -> str:
        if self.name is not None:
            return self.name
        raise AttributeError("No resource name provided")

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


@dataclass(frozen=True)
class Button:
    """A button for interactive notifications"""

    title: str
    """The localized button title"""

    on_pressed: Callable[[], Any] | None = None
    """Method to call when the button is pressed"""

    identifier: str = dataclasses.field(default_factory=uuid_str)
    """A unique identifier to use in callbacks to specify with button was clicked"""

    def __post_init__(self) -> None:
        if self.identifier is None:
            object.__setattr__(self, "identifier", uuid_str())


@dataclass(frozen=True)
class ReplyField:
    """A text field for interactive notifications"""

    title: str = "Reply"
    """A title for the field itself. On macOS, this will be the title of a button to
    show the field."""

    button_title: str = "Send"
    """The title of the button to send the reply"""

    on_replied: Callable[[str], Any] | None = None
    """Method to call when the 'reply' button is pressed"""


@dataclass(frozen=True)
class Notification:
    """A desktop notification

    Some properties of a notification may be ignored or interpreted differently
    depending on the platform.

    Callbacks for interactions will be executed on the Python process that scheduled the
    notification and only as long as the DesktopNotifier instance that scheduled the
    notification still exists.

    Install handlers on the DesktopNotifier instance itself to respond to interactions
    with notification from your app while it was not running.
    """

    title: str
    """Notification title"""

    message: str
    """Notification message"""

    urgency: Urgency = field(default=Urgency.Normal, repr=False)
    """Notification urgency. Can determine stickiness, notification appearance and
    break through silencing."""

    icon: Icon | None = field(default=None, repr=False)
    """Icon to use for the notification"""

    buttons: tuple[Button, ...] = field(default_factory=tuple, repr=False)
    """Buttons shown on an interactive notification"""

    buttons_dict: immutabledict[str, Button] = field(
        default_factory=immutabledict, init=False, repr=False, compare=False
    )
    """Buttons shown on an interactive notification, indexed by button identifier"""

    reply_field: ReplyField | None = field(default=None, repr=False)
    """Text field shown on an interactive notification. This can be used for example
    for messaging apps to reply directly from the notification."""

    on_dispatched: Callable[[], Any] | None = field(default=None, repr=False)
    """Method to call when the notification was sent to the notifications server for display"""

    on_cleared: Callable[[], Any] | None = field(default=None, repr=False)
    """Method to call when the notification is cleared without user interaction"""

    on_clicked: Callable[[], Any] | None = field(default=None, repr=False)
    """Method to call when the notification is clicked"""

    on_dismissed: Callable[[], Any] | None = field(default=None, repr=False)
    """Method to call when the notification is dismissed"""

    attachment: Attachment | None = field(default=None, repr=False)
    """A file attached to the notification which may be displayed as a preview"""

    sound: Sound | None = field(default=None, repr=False)
    """A sound to play on notification"""

    thread: str | None = field(default=None, repr=False)
    """An identifier to group related notifications together, e.g., from a chat space"""

    timeout: float = field(default=-1, repr=False)
    """Duration in seconds for which the notification is shown"""

    identifier: str = field(default_factory=uuid_str)
    """A unique identifier for this notification. Generated automatically if not
    passed by the client."""

    def __post_init__(self) -> None:
        if self.identifier is None:
            object.__setattr__(self, "identifier", uuid_str())

        object.__setattr__(
            self,
            "buttons_dict",
            immutabledict({button.identifier: button for button in self.buttons}),
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

    ON_DISPATCHED = auto()
    """Supports on-dispatched callbacks"""

    ON_CLEARED = auto()
    """Supports distinguishing between an user closing a notification, and clearing a
    notification programmatically, and consequently supports on-cleared callbacks"""

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
