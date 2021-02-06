# -*- coding: utf-8 -*-
"""
Dummy backend for unsupported platforms.
"""

# system imports
from typing import Optional

# local imports
from .base import Notification, DesktopNotifierBase


class DummyNotificationCenter(DesktopNotifierBase):
    """A dummy backend for unsupported platforms"""

    def __init__(self, app_name: str = "Python", notification_limit: int = 5) -> None:
        super().__init__(app_name, notification_limit)

    def _send(
        self,
        notification: Notification,
        notification_to_replace: Optional[Notification],
    ) -> str:
        pass

    def _clear_all(self) -> None:
        pass
