# -*- coding: utf-8 -*-
"""
Dummy backend for unsupported platforms
"""
from __future__ import annotations

from ..common import Capability, Notification
from .base import DesktopNotifierBackend


class DummyNotificationCenter(DesktopNotifierBackend):
    """A dummy backend for unsupported platforms"""

    def __init__(self, app_name: str) -> None:
        super().__init__(app_name)

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

    async def _send(self, notification: Notification) -> None:
        pass

    async def _clear(self, identifier: str) -> None:
        pass

    async def _clear_all(self) -> None:
        pass

    async def get_capabilities(self) -> frozenset[Capability]:
        return frozenset()
