# -*- coding: utf-8 -*-
"""
Dummy backend for unsupported platforms.
"""

from __future__ import annotations

# system imports
import uuid

# local imports
from .base import Notification, DesktopNotifierBase


class DummyNotificationCenter(DesktopNotifierBase):
    """A dummy backend for unsupported platforms"""

    def __init__(
        self,
        app_name: str = "Python",
        notification_limit: int | None = None,
    ) -> None:
        super().__init__(app_name, notification_limit)

    async def request_authorisation(self) -> bool:
        """
        Request authorisation to send notifications.

        :returns: Whether authorisation has been granted.
        """
        return True

    async def has_authorisation(self) -> bool:
        """
        Whether we have authorisation to send notifications.
        """
        return True

    async def _send(
        self,
        notification: Notification,
        notification_to_replace: Notification | None,
    ) -> str:
        if notification_to_replace:
            return str(notification_to_replace.identifier)
        else:
            return str(uuid.uuid4())

    async def _clear(self, notification: Notification) -> None:
        pass

    async def _clear_all(self) -> None:
        pass
