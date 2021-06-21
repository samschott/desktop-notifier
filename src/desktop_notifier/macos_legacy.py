# -*- coding: utf-8 -*-
"""
NSUserNotificationCenter backend for macOS.

* Should be used for macOS 10.13 and earlier.
* Deprecated but still available in macOS 11.0.
* Requires a running CFRunLoop to invoke callbacks.

"""

# system imports
import uuid
import platform
import logging
from typing import Optional, cast

# external imports
from rubicon.objc import NSObject, ObjCClass, objc_method, py_from_ns  # type: ignore
from rubicon.objc.runtime import load_library  # type: ignore

# local imports
from .base import Notification, DesktopNotifierBase


__all__ = ["CocoaNotificationCenterLegacy"]

logger = logging.getLogger(__name__)
macos_version, *_ = platform.mac_ver()

foundation = load_library("Foundation")

NSUserNotification = ObjCClass("NSUserNotification")
NSUserNotificationCenter = ObjCClass("NSUserNotificationCenter")
NSDate = ObjCClass("NSDate")

NSUserNotificationActivationTypeContentsClicked = 1
NSUserNotificationActivationTypeActionButtonClicked = 2
NSUserNotificationActivationTypeAdditionalActionClicked = 4

NSUserNotificationDefaultSoundName = "DefaultSoundName"


class NotificationCenterDelegate(NSObject):  # type: ignore
    """Delegate to handle user interactions with notifications"""

    @objc_method
    def userNotificationCenter_didActivateNotification_(
        self, center, notification
    ) -> None:

        platform_nid = py_from_ns(notification.identifier)
        py_notification = self.interface._notification_for_nid[platform_nid]
        py_notification = cast(Notification, py_notification)

        self.interface._clear_notification_from_cache(py_notification)

        if (
            notification.activationType
            == NSUserNotificationActivationTypeContentsClicked
        ):

            if py_notification.on_clicked:
                py_notification.on_clicked()

        elif (
            notification.activationType
            == NSUserNotificationActivationTypeActionButtonClicked
        ):

            callback = py_notification.buttons[0].on_pressed

            if callback:
                callback()


class CocoaNotificationCenterLegacy(DesktopNotifierBase):
    """NSUserNotificationCenter backend for macOS

    Should be used for macOS High Sierra and earlier. Supports only a single button per
    notification. Both app name and bundle identifier will be ignored. The notification
    center automatically uses the values provided by the app bundle or the Python
    framework.

    :param app_name: The name of the app. Does not have any effect because the app
        name is automatically determined from the bundle or framework.
    :param app_icon: The icon of the app. Does not have any effect because the app
        icon is automatically determined from the bundle or framework.
    :param notification_limit: Maximum number of notifications to keep in the system's
        notification center.
    """

    def __init__(
        self,
        app_name: str = "Python",
        app_icon: Optional[str] = None,
        notification_limit: Optional[int] = None,
    ) -> None:
        super().__init__(app_name, app_icon, notification_limit)

        self.nc = NSUserNotificationCenter.defaultUserNotificationCenter
        self.nc_delegate = NotificationCenterDelegate.alloc().init()
        self.nc_delegate.interface = self
        self.nc.delegate = self.nc_delegate

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
        notification_to_replace: Optional[Notification],
    ) -> str:
        """
        Uses NSUserNotificationCenter to schedule a notification.

        :param notification: Notification to send.
        :param notification_to_replace: Notification to replace, if any.
        """

        if notification_to_replace:
            platform_nid = str(notification_to_replace.identifier)
        else:
            platform_nid = str(uuid.uuid4())

        n = NSUserNotification.alloc().init()
        n.title = notification.title
        n.informativeText = notification.message
        n.identifier = platform_nid
        n.deliveryDate = NSDate.dateWithTimeInterval(0, sinceDate=NSDate.date())

        # store the notification instance for clearing
        notification._native = n  # type: ignore

        if notification.sound:
            n.soundName = NSUserNotificationDefaultSoundName

        if notification.buttons:
            if len(notification.buttons) > 1:
                logger.debug(
                    "NSUserNotificationCenter: only a single button is supported"
                )
            n.hasActionButton = True
            n.actionButtonTitle = notification.buttons[0].title

        self.nc.scheduleNotification(n)

        return platform_nid

    async def _clear(self, notification: Notification) -> None:
        """
        Removes a notifications from the notification center

        :param notification: Notification to clear.
        """

        if hasattr(notification, "_native"):
            self.nc.removeDeliveredNotification(notification._native)  # type: ignore

    async def _clear_all(self) -> None:
        """
        Clears all notifications from notification center
        """

        self.nc.removeAllDeliveredNotifications()
