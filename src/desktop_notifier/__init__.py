# -*- coding: utf-8 -*-
"""
Desktop notifications for Windows, Linux, macOS, iOS and iPadOS.
"""
from .main import (
    DEFAULT_ICON,
    DEFAULT_SOUND,
    Attachment,
    Button,
    Capability,
    DesktopNotifier,
    Icon,
    Notification,
    ReplyField,
    Sound,
    Urgency,
)
from .sync import DesktopNotifierSync

__version__ = "6.0.0"
__author__ = "Sam Schott"
__url__ = "https://github.com/samschott/desktop-notifier"

__all__ = [
    "__version__",
    "__author__",
    "__url__",
    "Notification",
    "Button",
    "ReplyField",
    "Urgency",
    "Icon",
    "Sound",
    "Attachment",
    "DesktopNotifier",
    "DesktopNotifierSync",
    "Capability",
    "DEFAULT_SOUND",
    "DEFAULT_ICON",
]
