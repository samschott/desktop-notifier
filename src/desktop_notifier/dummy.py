# -*- coding: utf-8 -*-
"""
Dummy backend for unsupported platforms.
"""

# system imports
import uuid
from typing import Optional, Callable, Any

# local imports
from .base import Notification, DesktopNotifierBase


class DummyNotificationCenter(DesktopNotifierBase):
    """A dummy backend for unsupported platforms"""

    def __init__(
        self,
        app_name: str = "Python",
        app_icon: Optional[str] = None,
        notification_limit: Optional[int] = None,
    ) -> None:
        super().__init__(app_name, app_icon, notification_limit)

    def request_authorisation(
        self, callback: Optional[Callable[[bool, str], Any]]
    ) -> None:
        """
        Request authorisation to send notifications.
        """
        if callback:
            callback(True, "")

    @property
    def has_authorisation(self) -> bool:
        """
        Whether we have authorisation to send notifications.
        """
        return True

    def _send(
        self,
        notification: Notification,
        notification_to_replace: Optional[Notification],
    ) -> str:
        if notification_to_replace:
            return str(notification_to_replace.identifier)
        else:
            return str(uuid.uuid4())

    def _clear(self, notification: Notification) -> None:
        pass

    def _clear_all(self) -> None:
        pass
