# -*- coding: utf-8 -*-
"""
Synchronous desktop notification API
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, Sequence, TypeVar

from .common import (
    DEFAULT_ICON,
    Attachment,
    Button,
    Capability,
    Icon,
    Notification,
    ReplyField,
    Sound,
    Urgency,
)
from .main import DesktopNotifier

__all__ = ["DesktopNotifierSync"]


T = TypeVar("T")


class DesktopNotifierSync:
    """
    A synchronous counterpart to :class:`desktop_notifier.main.DesktopNotifier`

    .. warning::
        Callbacks on interaction with the notification will not work on macOS or Linux
        without a running event loop.
    """

    def __init__(
        self,
        app_name: str = "Python",
        app_icon: Icon | None = DEFAULT_ICON,
        notification_limit: int | None = None,
    ) -> None:
        self._async_api = DesktopNotifier(app_name, app_icon)
        self._loop = asyncio.new_event_loop()

    def _run_coro_sync(self, coro: Coroutine[None, None, T]) -> T:
        # Make sure to always use the same loop because async queues, future, etc. are
        # always bound to a loop.
        if self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            res = future.result()
        else:
            res = self._loop.run_until_complete(coro)

        return res

    @property
    def app_name(self) -> str:
        """The application name"""
        return self._async_api.app_name

    @app_name.setter
    def app_name(self, value: str) -> None:
        """Setter: app_name"""
        self._async_api.app_name = value

    def request_authorisation(self) -> bool:
        """See :meth:`desktop_notifier.main.DesktopNotifier.request_authorisation`"""
        coro = self._async_api.request_authorisation()
        return self._run_coro_sync(coro)

    def has_authorisation(self) -> bool:
        """See :meth:`desktop_notifier.main.DesktopNotifier.has_authorisation`"""
        coro = self._async_api.has_authorisation()
        return self._run_coro_sync(coro)

    def send_notification(self, notification: Notification) -> str:
        """See :meth:`desktop_notifier.main.DesktopNotifier.send_notification`"""
        coro = self._async_api.send_notification(notification)
        return self._run_coro_sync(coro)

    def send(
        self,
        title: str,
        message: str,
        urgency: Urgency = Urgency.Normal,
        icon: Icon | None = None,
        buttons: Sequence[Button] = (),
        reply_field: ReplyField | None = None,
        on_clicked: Callable[[], Any] | None = None,
        on_dismissed: Callable[[], Any] | None = None,
        attachment: Attachment | None = None,
        sound: Sound | None = None,
        thread: str | None = None,
        timeout: int = -1,  # in seconds
    ) -> str:
        """See :meth:`desktop_notifier.main.DesktopNotifier.send`"""
        notification = Notification(
            title,
            message,
            urgency=urgency,
            icon=icon,
            buttons=tuple(buttons),
            reply_field=reply_field,
            on_clicked=on_clicked,
            on_dismissed=on_dismissed,
            attachment=attachment,
            sound=sound,
            thread=thread,
            timeout=timeout,
        )
        coro = self._async_api.send_notification(notification)
        return self._run_coro_sync(coro)

    def get_current_notifications(self) -> list[str]:
        """See :meth:`desktop_notifier.main.DesktopNotifier.get_current_notifications`"""
        coro = self._async_api.get_current_notifications()
        return self._run_coro_sync(coro)

    def clear(self, identifier: str) -> None:
        """See :meth:`desktop_notifier.main.DesktopNotifier.notification`"""
        coro = self._async_api.clear(identifier)
        return self._run_coro_sync(coro)

    def clear_all(self) -> None:
        """See :meth:`desktop_notifier.main.DesktopNotifier.clear_all`"""
        coro = self._async_api.clear_all()
        return self._run_coro_sync(coro)

    def get_capabilities(self) -> frozenset[Capability]:
        """See :meth:`desktop_notifier.main.DesktopNotifier.get_capabilities`"""
        coro = self._async_api.get_capabilities()
        return self._run_coro_sync(coro)
