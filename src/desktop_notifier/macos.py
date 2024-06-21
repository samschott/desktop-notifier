# -*- coding: utf-8 -*-
"""
UNUserNotificationCenter backend for macOS

* Introduced in macOS 10.14.
* Cross-platform with iOS and iPadOS.
* Only available from signed app bundles if called from the main executable or from a
  signed Python framework (for example from python.org).
* Requires a running CFRunLoop to invoke callbacks.
"""
# system imports
import shutil
import tempfile
import uuid
import logging
import enum
import asyncio
from pathlib import Path
from concurrent.futures import Future
from typing import cast, Optional

# external imports
from packaging.version import Version
from rubicon.objc import NSObject, ObjCClass, objc_method, py_from_ns
from rubicon.objc.runtime import load_library, objc_id, objc_block

# local imports
from .base import (
    Notification,
    DesktopNotifierBase,
    Urgency,
    Capability,
    DEFAULT_SOUND,
)
from .macos_support import macos_version


__all__ = ["CocoaNotificationCenter"]

logger = logging.getLogger(__name__)

foundation = load_library("Foundation")
uns = load_library("UserNotifications")

UNUserNotificationCenter = ObjCClass("UNUserNotificationCenter")
UNMutableNotificationContent = ObjCClass("UNMutableNotificationContent")
UNNotificationRequest = ObjCClass("UNNotificationRequest")
UNNotificationAction = ObjCClass("UNNotificationAction")
UNTextInputNotificationAction = ObjCClass("UNTextInputNotificationAction")
UNNotificationCategory = ObjCClass("UNNotificationCategory")
UNNotificationSound = ObjCClass("UNNotificationSound")
UNNotificationAttachment = ObjCClass("UNNotificationAttachment")
UNNotificationSettings = ObjCClass("UNNotificationSettings")

NSURL = ObjCClass("NSURL")
NSSet = ObjCClass("NSSet")
NSError = ObjCClass("NSError")

# UserNotifications.h

UNNotificationDefaultActionIdentifier = (
    "com.apple.UNNotificationDefaultActionIdentifier"
)
UNNotificationDismissActionIdentifier = (
    "com.apple.UNNotificationDismissActionIdentifier"
)
ReplyActionIdentifier = "com.desktop-notifier.ReplyActionIdentifier"

UNAuthorizationOptionBadge = 1 << 0
UNAuthorizationOptionSound = 1 << 1
UNAuthorizationOptionAlert = 1 << 2

UNNotificationActionOptionAuthenticationRequired = 1 << 0
UNNotificationActionOptionDestructive = 1 << 1
UNNotificationActionOptionForeground = 1 << 2
UNNotificationActionOptionNone = 0

UNNotificationCategoryOptionNone = 0

UNAuthorizationStatusAuthorized = 2
UNAuthorizationStatusProvisional = 3
UNAuthorizationStatusEphemeral = 4


class UNNotificationInterruptionLevel(enum.Enum):
    Passive = 0
    Active = 1
    TimeSensitive = 2
    Critical = 3


class NotificationCenterDelegate(NSObject):  # type:ignore
    """Delegate to handle user interactions with notifications"""

    @objc_method  # type:ignore
    def userNotificationCenter_didReceiveNotificationResponse_withCompletionHandler_(
        self, center, response, completion_handler: objc_block
    ) -> None:
        # Get the notification which was clicked from the platform ID.
        platform_nid = py_from_ns(response.notification.request.identifier)
        py_notification = self.interface._notification_for_nid[platform_nid]
        py_notification = cast(Notification, py_notification)

        self.interface._clear_notification_from_cache(py_notification)

        # Invoke the callback which corresponds to the user interaction.
        if response.actionIdentifier == UNNotificationDefaultActionIdentifier:
            if py_notification.on_clicked:
                py_notification.on_clicked()

        elif response.actionIdentifier == UNNotificationDismissActionIdentifier:
            if py_notification.on_dismissed:
                py_notification.on_dismissed()

        elif response.actionIdentifier == ReplyActionIdentifier:
            if py_notification.reply_field.on_replied:
                reply_text = py_from_ns(response.userText)
                py_notification.reply_field.on_replied(reply_text)

        else:
            button_number = int(py_from_ns(response.actionIdentifier))
            callback = py_notification.buttons[button_number].on_pressed

            if callback:
                callback()

        completion_handler()


class CocoaNotificationCenter(DesktopNotifierBase):
    """UNUserNotificationCenter backend for macOS

    Can be used with macOS Catalina and newer. Both app name and bundle identifier
    will be ignored. The notification center automatically uses the values provided
    by the app bundle.

    :param app_name: The name of the app. Does not have any effect because the app
        name is automatically determined from the bundle or framework.
    :param notification_limit: Maximum number of notifications to keep in the system's
        notification center.
    """

    _to_native_urgency = {
        Urgency.Low: UNNotificationInterruptionLevel.Passive,
        Urgency.Normal: UNNotificationInterruptionLevel.Active,
        Urgency.Critical: UNNotificationInterruptionLevel.TimeSensitive,
    }

    def __init__(
        self,
        app_name: str = "Python",
        notification_limit: Optional[int] = None,
    ) -> None:
        super().__init__(app_name, notification_limit)
        self.nc = UNUserNotificationCenter.currentNotificationCenter()
        self.nc_delegate = NotificationCenterDelegate.alloc().init()
        self.nc_delegate.interface = self
        self.nc.delegate = self.nc_delegate

        self._clear_notification_categories()

    async def request_authorisation(self) -> bool:
        """
        Request authorisation to send user notifications. If this is called for the
        first time for an app, the call will only return once the user has granted or
        denied the request. Otherwise, the call will just return the current
        authorisation status without prompting the user.

        :returns: Whether authorisation has been granted.
        """
        future: Future[tuple[bool, str]] = Future()

        def on_auth_completed(granted: bool, error: objc_id) -> None:
            ns_error = py_from_ns(error)
            if ns_error:
                ns_error.retain()
            future.set_result((granted, ns_error))

        self.nc.requestAuthorizationWithOptions(
            UNAuthorizationOptionAlert
            | UNAuthorizationOptionSound
            | UNAuthorizationOptionBadge,
            completionHandler=on_auth_completed,
        )

        has_authorization, error = await asyncio.wrap_future(future)

        if error:
            log_nserror(error, "Authorisation denied")
            error.autorelease()  # type:ignore[attr-defined]

        return has_authorization

    async def has_authorisation(self) -> bool:
        """Whether we have authorisation to send notifications."""
        future: Future[UNNotificationSettings] = Future()  # type:ignore[valid-type]

        def handler(settings: objc_id) -> None:
            settings = py_from_ns(settings)
            settings.retain()
            future.set_result(settings)

        self.nc.getNotificationSettingsWithCompletionHandler(handler)

        settings = await asyncio.wrap_future(future)
        authorized = settings.authorizationStatus in (  # type:ignore[attr-defined]
            UNAuthorizationStatusAuthorized,
            UNAuthorizationStatusProvisional,
            UNAuthorizationStatusEphemeral,
        )
        settings.autorelease()  # type:ignore[attr-defined]

        return authorized

    async def _send(
        self,
        notification: Notification,
        notification_to_replace: Optional[Notification],
    ) -> None:
        """
        Uses UNUserNotificationCenter to schedule a notification.

        :param notification: Notification to send.
        :param notification_to_replace: Notification to replace, if any.
        """
        if notification_to_replace:
            platform_nid = notification_to_replace.identifier
        else:
            platform_nid = str(uuid.uuid4())

        # On macOS, we need to register a new notification category for every
        # unique set of buttons.
        category_id = await self._create_category_for_notification(notification)

        # Create the native notification and notification request.
        content = UNMutableNotificationContent.alloc().init()
        content.title = notification.title
        content.body = notification.message
        content.categoryIdentifier = category_id
        content.threadIdentifier = notification.thread
        if macos_version >= Version("12.0"):
            content.interruptionLevel = self._to_native_urgency[notification.urgency]

        if notification.sound:
            if notification.sound == DEFAULT_SOUND:
                content.sound = UNNotificationSound.defaultSound
            elif notification.sound.name:
                content.sound = UNNotificationSound.soundNamed(notification.sound.name)

        if notification.attachment:
            # Copy attachment to temporary file to ensure that it exists and that we can
            # access it. Invalid file paths can otherwise cause a segfault when creating
            # UNNotificationAttachment. The temporary file will be deleted by macOS
            # after usage.
            attachment_path = notification.attachment.as_path()
            tmp_dir = tempfile.mkdtemp()
            try:
                tmp_path = Path(tmp_dir) / attachment_path.name
                shutil.copy(attachment_path, tmp_path)
            except OSError:
                logger.warning("Could not access attachment file", exc_info=True)
            else:
                url = NSURL.fileURLWithPath(str(tmp_path), isDirectory=False)
                attachment = UNNotificationAttachment.attachmentWithIdentifier(
                    "", URL=url, options={}, error=None
                )
                content.attachments = [attachment]

        notification_request = UNNotificationRequest.requestWithIdentifier(
            platform_nid, content=content, trigger=None
        )

        future: Future[NSError] = Future()  # type:ignore[valid-type]

        def handler(error: objc_id) -> None:
            ns_error = py_from_ns(error)
            if ns_error:
                ns_error.retain()
            future.set_result(ns_error)

        # Post the notification.
        self.nc.addNotificationRequest(
            notification_request, withCompletionHandler=handler
        )

        # Error handling.
        error = await asyncio.wrap_future(future)

        if error:
            log_nserror(error, "Error when scheduling notification")
            error.autorelease()  # type:ignore[attr-defined]

        notification.identifier = platform_nid

    async def _create_category_for_notification(
        self, notification: Notification
    ) -> Optional[str]:
        """
        Registers a new notification category with UNNotificationCenter for the given
        notification or retrieves an existing one if it exists for our set of buttons.

        :param notification: Notification instance.
        :returns: The identifier of the existing or created notification category.
        """
        if not (notification.buttons or notification.reply_field):
            return None

        button_titles = tuple(notification.buttons)
        ui_repr = f"buttons={button_titles}, reply_field={notification.reply_field}"
        category_id = f"desktop-notifier: {ui_repr}"

        # Retrieve existing categories. We do not cache this value because it may be
        # modified by other Python processes using desktop-notifier.
        categories = await self._get_notification_categories()
        category_ids = set(
            py_from_ns(c.identifier)
            for c in categories.allObjects()  # type:ignore[attr-defined]
        )

        # Register new category if necessary.
        if category_id not in category_ids:
            # Create action for each button.
            actions = []

            if notification.reply_field:
                action = UNTextInputNotificationAction.actionWithIdentifier(
                    ReplyActionIdentifier,
                    title=notification.reply_field.title,
                    options=UNNotificationActionOptionNone,
                    textInputButtonTitle=notification.reply_field.button_title,
                    textInputPlaceholder="",
                )
                actions.append(action)

            for n, button in enumerate(notification.buttons):
                action = UNNotificationAction.actionWithIdentifier(
                    str(n), title=button.title, options=UNNotificationActionOptionNone
                )
                actions.append(action)

            # Add category for new set of buttons.
            new_categories = categories.setByAddingObject(  # type:ignore[attr-defined]
                UNNotificationCategory.categoryWithIdentifier(
                    category_id,
                    actions=actions,
                    intentIdentifiers=[],
                    options=UNNotificationCategoryOptionNone,
                )
            )
            self.nc.setNotificationCategories(new_categories)

        return category_id

    async def _get_notification_categories(self) -> NSSet:  # type:ignore[valid-type]
        """Returns the registered notification categories for this app / Python."""
        future: Future[NSSet] = Future()  # type:ignore[valid-type]

        def handler(categories: objc_id) -> None:
            categories = py_from_ns(categories)
            categories.retain()
            future.set_result(categories)

        self.nc.getNotificationCategoriesWithCompletionHandler(handler)

        categories = await asyncio.wrap_future(future)
        categories.autorelease()  # type:ignore[attr-defined]

        return categories

    def _clear_notification_categories(self) -> None:
        """Clears all registered notification categories for this application."""
        empty_set = NSSet.alloc().init()
        self.nc.setNotificationCategories(empty_set)

    async def _clear(self, notification: Notification) -> None:
        """
        Removes a notifications from the notification center

        :param notification: Notification to clear.
        """
        self.nc.removeDeliveredNotificationsWithIdentifiers([notification.identifier])

    async def _clear_all(self) -> None:
        """
        Clears all notifications from notification center. This method does not affect
        any notification requests that are scheduled, but have not yet been delivered.
        """
        self.nc.removeAllDeliveredNotifications()

    async def get_capabilities(self) -> frozenset[Capability]:
        capabilities = {
            Capability.TITLE,
            Capability.MESSAGE,
            Capability.BUTTONS,
            Capability.REPLY_FIELD,
            Capability.ON_CLICKED,
            Capability.ON_DISMISSED,
            Capability.SOUND,
            Capability.SOUND_NAME,
            Capability.THREAD,
            Capability.ATTACHMENT,
        }
        if macos_version >= Version("12.0"):
            capabilities.add(Capability.URGENCY)

        return frozenset(capabilities)


def log_nserror(error: NSError, prefix: str) -> None:  # type:ignore[valid-type]
    domain = str(error.domain)  # type:ignore[attr-defined]
    code = int(error.code)  # type:ignore[attr-defined]
    description = str(error.localizedDescription)  # type:ignore[attr-defined]

    logger.warning(
        "%s: domain=%s, code=%s, description=%s", prefix, domain, code, description
    )
