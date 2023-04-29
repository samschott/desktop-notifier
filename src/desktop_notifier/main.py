# -*- coding: utf-8 -*-
"""
This module handles desktop notifications and supports multiple backends, depending on
the platform.
"""

# system imports
import platform
from threading import RLock
import logging
import asyncio
from pathlib import Path
from typing import (
    Type,
    Union,
    Optional,
    Callable,
    Coroutine,
    List,
    Any,
    TypeVar,
    Sequence,
)

# external imports
from packaging.version import Version

# local imports
from .base import (
    Urgency,
    Button,
    ReplyField,
    Notification,
    DesktopNotifierBase,
    PYTHON_ICON_PATH,
)

__all__ = [
    "Notification",
    "Button",
    "ReplyField",
    "Urgency",
    "DesktopNotifier",
]

logger = logging.getLogger(__name__)

T = TypeVar("T")


default_event_loop_policy = asyncio.DefaultEventLoopPolicy()


def get_implementation() -> Type[DesktopNotifierBase]:
    """
    Return the backend class depending on the platform and version.

    :returns: A desktop notification backend suitable for the current platform.
    :raises RuntimeError: when passing ``macos_legacy = True`` on macOS 12.0 and later.
    """
    if platform.system() == "Darwin":
        from .macos_support import is_bundle, is_signed_bundle, macos_version

        has_unusernotificationcenter = macos_version >= Version("10.14")
        has_nsusernotificationcenter = macos_version < Version("12.0")
        is_signed = is_signed_bundle()

        if has_unusernotificationcenter and is_signed:
            # Use modern UNUserNotificationCenter.
            from .macos import CocoaNotificationCenter

            return CocoaNotificationCenter

        elif has_nsusernotificationcenter and is_bundle():
            if has_unusernotificationcenter and not is_signed:
                logger.warning(
                    "Running outside of a signed Framework or bundle: "
                    "falling back to NSUserNotificationCenter"
                )
            else:
                logger.warning(
                    "Running on macOS 10.13 or earlier: "
                    "falling back to NSUserNotificationCenter"
                )

            # Use deprecated NSUserNotificationCenter.
            from .macos_legacy import CocoaNotificationCenterLegacy

            return CocoaNotificationCenterLegacy

        else:
            # Use dummy backend.
            logger.warning(
                "Notification Center can only be used "
                "from a signed Framework or app bundle"
            )

            from .dummy import DummyNotificationCenter

            return DummyNotificationCenter

    elif platform.system() == "Linux":
        from .dbus import DBusDesktopNotifier

        return DBusDesktopNotifier

    elif platform.system() == "Windows" and Version(platform.version()) >= Version(
        "10.0.10240"
    ):
        from .winrt import WinRTDesktopNotifier

        return WinRTDesktopNotifier

    else:
        from .dummy import DummyNotificationCenter

        return DummyNotificationCenter


class DesktopNotifier:
    """Cross-platform desktop notification emitter

    Uses different backends depending on the platform version and available services.
    All implementations will dispatch notifications without an event loop but will
    require a running event loop to execute callbacks when the end user interacts with a
    notification. On Linux, a asyncio event loop is required. On macOS, a CFRunLoop *in
    the main thread* is required. Packages such as :mod:`rubicon.objc` can be used to
    integrate asyncio with a CFRunLoop.

    :param app_name: Name to identify the application in the notification center. On
        Linux, this should correspond to the application name in a desktop entry. On
        macOS, this argument is ignored and the app is identified by the bundle ID of
        the sending program (e.g., Python).
    :param app_icon: Default icon to use for notifications. This should be either a URI
        string, a :class:`pathlib.Path` path, or a name in a freedesktop.org-compliant
        icon theme. If None, the icon of the calling application will be used if it
        can be determined. On macOS, this argument is ignored and the app icon is
        identified by the bundle ID of the sending program (e.g., Python).
    :param notification_limit: Maximum number of notifications to keep in the system's
        notification center. This may be ignored by some implementations.
    """

    def __init__(
        self,
        app_name: str = "Python",
        app_icon: Union[Path, str, None] = PYTHON_ICON_PATH,
        notification_limit: Optional[int] = None,
    ) -> None:
        impl_cls = get_implementation()

        if isinstance(app_icon, Path):
            app_icon = app_icon.as_uri()

        self._lock = RLock()
        self._impl = impl_cls(app_name, app_icon, notification_limit)
        self._did_request_authorisation = False

        # Use our own event loop for the sync API so that we don't interfere with any
        # other ansycio event loops / threads, etc.
        self._loop = default_event_loop_policy.new_event_loop()

    def _run_coro_sync(self, coro: Coroutine[None, None, T]) -> T:
        """
        Runs the given coroutine and returns the result synchronously. This is used as a
        wrapper to conveniently convert the async API calls to synchronous ones.
        """
        if self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            res = future.result()
        else:
            res = self._loop.run_until_complete(coro)

        return res

    @property
    def app_name(self) -> str:
        """The application name"""
        return self._impl.app_name

    @app_name.setter
    def app_name(self, value: str) -> None:
        """Setter: app_name"""
        self._impl.app_name = value

    @property
    def app_icon(self) -> Optional[str]:
        """The application icon: a URI for a local file or an icon name."""
        return self._impl.app_icon

    @app_icon.setter
    def app_icon(self, value: Union[Path, str, None]) -> None:
        """Setter: app_icon"""
        if isinstance(value, Path):
            value = value.as_uri()

        self._impl.app_icon = value

    async def request_authorisation(self) -> bool:
        """
        Requests authorisation to send user notifications. This will be automatically
        called for you when sending a notification for the first time. It also can be
        called manually to request authorisation in advance.

        On some platforms such as macOS and iOS, a prompt will be shown to the user
        when this method is called for the first time. This method does nothing on
        platforms where user authorisation is not required.

        :returns: Whether authorisation has been granted.
        """
        with self._lock:
            self._did_request_authorisation = True
            return await self._impl.request_authorisation()

    async def has_authorisation(self) -> bool:
        """Returns whether we have authorisation to send notifications."""
        return await self._impl.has_authorisation()

    async def send(
        self,
        title: str,
        message: str,
        urgency: Urgency = Urgency.Normal,
        icon: Union[Path, str, None] = None,
        buttons: Sequence[Button] = (),
        reply_field: Optional[ReplyField] = None,
        on_clicked: Optional[Callable[[], Any]] = None,
        on_dismissed: Optional[Callable[[], Any]] = None,
        on_timeout: Optional[Callable[[], Any]] = None,
        attachment: Union[Path, str, None] = None,
        sound: bool = False,
        thread: Optional[str] = None,
        timeout: int = -1,
    ) -> Notification:
        """
        Sends a desktop notification.

        Some arguments may be ignored, depending on the backend.

        This method will always return a :class:`base.Notification` instance and will
        not raise an exception when scheduling the notification fails. If the
        notification was scheduled successfully, its ``identifier`` will be set to the
        platform's native notification identifier. Otherwise, the ``identifier`` will be
        ``None``.

        Note that even a successfully scheduled notification may not be displayed to the
        user, depending on their notification center settings (for instance if "do not
        disturb" is enabled on macOS).

        :param title: Notification title.
        :param message: Notification message.
        :param urgency: Notification level: low, normal or critical. This may be
            interpreted differently by some implementations, for instance causing the
            notification to remain visible for longer, or may be ignored.
        :param icon: Optional URI string, :class:`pathlib.Path` or icon name to use. If
            given, this will replace the icon specified by :attr:`app_icon`. Will be
            ignored on macOS.
        :param buttons: A list of buttons with callbacks for the notification.
        :param reply_field: Optional reply field to show with the notification. Can be
            used for instance in chat apps.
        :param on_clicked: Optional callback to call when the notification is clicked.
            The callback will be called without any arguments. This is ignored by some
            implementations.
        :param on_dismissed: Optional callback to call when the notification is
            dismissed. The callback will be called without any arguments. This is
            ignored by some implementations.
        :param on_timeout: Optional callback to call when the notification is
            timed out. The callback will be called without any arguments. This is
            ignored by some implementations.
        :param attachment: Optional URI string or :class:`pathlib.Path` for an
            attachment to the notification such as an image, movie, or audio file. A
            preview of this may be displayed together with the notification. Different
            platforms and Linux notification servers support different types of
            attachments. Please consult the platform support section of the
            documentation.
        :param sound: Whether to play a sound when the notification is shown. The
            platform's default sound will be used, where available.
        :param thread: An identifier to group related notifications together. This is
            ignored on Linux.
        :param timeout: The duration (in seconds) for which the notification is shown
            unless dismissed. Only supported on Linux. Default is ``-1`` which implies
            OS-specified.

        :returns: The scheduled notification instance.
        """
        if icon is None:
            icon = self.app_icon
        elif isinstance(icon, Path):
            icon = icon.as_uri()

        if isinstance(attachment, Path):
            attachment = attachment.as_uri()

        notification = Notification(
            title,
            message,
            urgency,
            icon,
            buttons,
            reply_field,
            on_clicked,
            on_dismissed,
            attachment,
            sound,
            thread,
            timeout,
        )

        with self._lock:
            # Ask for authorisation if not already done. On some platforms, this will
            # trigger a system dialog to ask the user for permission.
            if not self._did_request_authorisation:
                await self.request_authorisation()

            # We attempt to send the notification regardless of authorization.
            # The user may have changed settings in the meantime.
            await self._impl.send(notification)

            async def timeout_task():
                await asyncio.sleep(timeout)
                if notification in self.current_notifications:
                    # The notification may have been dismissed in the meantime
                    await self.clear(notification)
                    if on_timeout:
                        on_timeout()

            if timeout > 0:
                asyncio.create_task(timeout_task())

            return notification

    def send_sync(
        self,
        title: str,
        message: str,
        urgency: Urgency = Urgency.Normal,
        icon: Union[Path, str, None] = None,
        buttons: Sequence[Button] = (),
        reply_field: Optional[ReplyField] = None,
        on_clicked: Optional[Callable[[], Any]] = None,
        on_dismissed: Optional[Callable[[], Any]] = None,
        on_timeout: Optional[Callable[[], Any]] = None,
        attachment: Union[Path, str, None] = None,
        sound: bool = False,
        thread: Optional[str] = None,
        timeout: int = -1,
    ) -> Notification:
        """
        Synchronous call of :meth:`send`, for use without an asyncio event loop.

        :returns: The scheduled notification instance.
        """
        coro = self.send(
            title,
            message,
            urgency,
            icon,
            buttons,
            reply_field,
            on_clicked,
            on_dismissed,
            on_timeout,
            attachment,
            sound,
            thread,
            timeout,
        )
        return self._run_coro_sync(coro)

    @property
    def current_notifications(self) -> List[Notification]:
        """A list of all currently displayed notifications for this app"""
        return self._impl.current_notifications

    async def clear(self, notification: Notification) -> None:
        """
        Removes the given notification from the notification center.

        :param notification: Notification to clear.
        """
        with self._lock:
            await self._impl.clear(notification)

    async def clear_all(self) -> None:
        """
        Removes all currently displayed notifications for this app from the notification
        center.
        """
        with self._lock:
            await self._impl.clear_all()
