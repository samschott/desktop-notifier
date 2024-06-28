# -*- coding: utf-8 -*-
"""
Desktop notifications for Windows, Linux, macOS, iOS and iPadOS.
"""
from importlib.metadata import version

from .main import (
    DesktopNotifier,
    Button,
    ReplyField,
    Notification,
    Urgency,
    Capability,
    Icon,
    Sound,
    Attachment,
    DEFAULT_SOUND,
    DEFAULT_ICON,
)
from .util.pkg_metadata_helper import (
    __DESKTOP_NOTIFIER_PACKAGE_NAME__,
    _get_primary_author_name,
    _get_project_url
)
from .sync import DesktopNotifierSync


__version__ = version(__DESKTOP_NOTIFIER_PACKAGE_NAME__)
__author__ = _get_primary_author_name()
__url__ = _get_project_url()

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
