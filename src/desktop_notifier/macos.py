# -*- coding: utf-8 -*-
"""
UNUserNotificationCenter backend for macOS.

* Introduced in macOS 10.14.
* Cross-platform with iOS and iPadOS.
* Only available from signed app bundles if called from the main executable or from a
  signed Python framework (for example from python.org).
* Requires a running CFRunLoop to invoke callbacks.

"""

# system imports
import uuid
import logging
from concurrent.futures import Future, wait
from typing import Optional, Dict, Tuple

# external imports
from rubicon.objc import NSObject, ObjCClass, objc_method, py_from_ns  # type: ignore
from rubicon.objc.runtime import load_library, objc_id, objc_block  # type: ignore

# local imports
from .base import Notification, DesktopNotifierBase


__all__ = ["CocoaNotificationCenter"]

logger = logging.getLogger(__name__)

foundation = load_library("Foundation")
uns = load_library("UserNotifications")

UNUserNotificationCenter = ObjCClass("UNUserNotificationCenter")
UNMutableNotificationContent = ObjCClass("UNMutableNotificationContent")
UNNotificationRequest = ObjCClass("UNNotificationRequest")
UNNotificationAction = ObjCClass("UNNotificationAction")
UNNotificationCategory = ObjCClass("UNNotificationCategory")
UNNotificationSound = ObjCClass("UNNotificationSound")

NSSet = ObjCClass("NSSet")

UNNotificationDefaultActionIdentifier = (
    "com.apple.UNNotificationDefaultActionIdentifier"
)
UNNotificationDismissActionIdentifier = (
    "com.apple.UNNotificationDismissActionIdentifier"
)

UNAuthorizationOptionBadge = 1 << 0
UNAuthorizationOptionSound = 1 << 1
UNAuthorizationOptionAlert = 1 << 2

UNNotificationActionOptionForeground = 1 << 2

UNNotificationCategoryOptionNone = 0

UNAuthorizationStatusAuthorized = 2
UNAuthorizationStatusProvisional = 3
UNAuthorizationStatusEphemeral = 4


class NotificationCenterDelegate(NSObject):  # type: ignore
    """Delegate to handle user interactions with notifications"""

    @objc_method
    def userNotificationCenter_didReceiveNotificationResponse_withCompletionHandler_(
        self, center, response, completion_handler: objc_block
    ) -> None:

        # Get the notification which was clicked from the platform ID.
        platform_nid = py_from_ns(response.notification.request.identifier)
        py_notification = self.interface._notification_for_nid[platform_nid]

        # Get and call the callback which corresponds to the user interaction.
        if response.actionIdentifier == UNNotificationDefaultActionIdentifier:

            callback = py_notification.action

            if callback:
                callback()

        elif response.actionIdentifier != UNNotificationDismissActionIdentifier:

            action_id_str = py_from_ns(response.actionIdentifier)

            callback = py_notification.buttons.get(action_id_str)

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
        self.nc = UNUserNotificationCenter.currentNotificationCenter()
        self.nc_delegate = NotificationCenterDelegate.alloc().init()
        self.nc_delegate.interface = self
        self.nc.delegate = self.nc_delegate

        self._did_request_authorisation = False
        self._notification_categories: Dict[Tuple[str, ...], str] = {}

    def request_authorisation(self) -> None:
        """
        Request authorisation to send user notifications. This method returns
        immediately but authorisation will only be granted once the user has accepted
        the prompt. Use :attr:`has_authorisation` to check if we are authorised.
        """

        def on_auth_completed(granted: bool, error: objc_id) -> None:
            if granted:
                logger.debug("Authorisation granted")
            else:
                logger.debug("Authorisation denied")

            if error:
                error = py_from_ns(error)
                logger.warning("Authorisation error %s", str(error))

        self.nc.requestAuthorizationWithOptions(
            UNAuthorizationOptionAlert
            | UNAuthorizationOptionSound
            | UNAuthorizationOptionBadge,
            completionHandler=on_auth_completed,
        )

        self._did_request_authorisation = True

    @property
    def has_authorisation(self) -> bool:
        """Whether we have authorisation to send notifications."""

        # get existing notification categories

        future: Future = Future()

        def handler(settings: objc_id) -> None:
            settings = py_from_ns(settings)
            settings.retain()
            future.set_result(settings)

        self.nc.getNotificationSettingsWithCompletionHandler(handler)

        wait([future])
        settings = future.result()

        authorized = settings.authorizationStatus in (
            UNAuthorizationStatusAuthorized,
            UNAuthorizationStatusProvisional,
            UNAuthorizationStatusEphemeral,
        )

        settings.release()

        return authorized

    def _send(
        self,
        notification: Notification,
        notification_to_replace: Optional[Notification],
    ) -> str:
        """
        Uses UNUserNotificationCenter to schedule a notification.

        :param notification: Notification to send.
        :param notification_to_replace: Notification to replace, if any.
        """

        if not self._did_request_authorisation:
            self.request_authorisation()

        if not self.has_authorisation:
            raise RuntimeError("Not authorised")

        if notification_to_replace:
            platform_nid = str(notification_to_replace.identifier)
        else:
            platform_nid = str(uuid.uuid4())

        # Set up buttons for notification. On macOS, we need need to register a new
        # notification category for every unique set of buttons.
        button_names = tuple(notification.buttons.keys())
        category_id = self._category_id_for_button_names(button_names)

        # Create the native notification + notification request.
        content = UNMutableNotificationContent.alloc().init()
        content.title = notification.title
        content.body = notification.message
        content.categoryIdentifier = category_id

        if notification.sound:
            content.sound = UNNotificationSound.defaultSound

        notification_request = UNNotificationRequest.requestWithIdentifier(
            platform_nid, content=content, trigger=None
        )

        # Post the notification.
        self.nc.addNotificationRequest(notification_request, withCompletionHandler=None)

        return platform_nid

    def _category_id_for_button_names(
        self, button_names: Tuple[str, ...]
    ) -> Optional[str]:
        """
        Creates and registers a new notification category with the given buttons
        or retrieves an existing one.

        :returns: UNUserNotificationCenter ID for a new or an exiting category. Returns
            None if a notification category without buttons is requested.
        """

        if not button_names:
            return None

        try:
            return self._notification_categories[button_names]
        except KeyError:
            actions = []

            for name in button_names:
                action = UNNotificationAction.actionWithIdentifier(
                    name, title=name, options=UNNotificationActionOptionForeground
                )
                actions.append(action)

            # get existing notification categories

            future: Future = Future()

            def handler(categories: objc_id) -> None:
                categories = py_from_ns(categories)
                categories.retain()
                future.set_result(categories)

            self.nc.getNotificationCategoriesWithCompletionHandler(handler)

            wait([future])
            categories = future.result()

            # add category for new set of buttons

            category_id = str(uuid.uuid4())
            new_categories = categories.setByAddingObject(
                UNNotificationCategory.categoryWithIdentifier(
                    category_id,
                    actions=actions,
                    intentIdentifiers=[],
                    options=UNNotificationCategoryOptionNone,
                )
            )
            self.nc.setNotificationCategories(new_categories)
            self._notification_categories[button_names] = category_id

            categories.release()

            return category_id

    def _clear(self, notification: Notification) -> None:
        """
        Removes a notifications from the notification center

        :param notification: Notification to clear.
        """
        self.nc.removeDeliveredNotificationsWithIdentifiers([notification.identifier])

    def _clear_all(self) -> None:
        """
        Clears all notifications from notification center

        The method executes asynchronously, returning immediately and removing the
        notifications on a background thread. This method does not affect any
        notification requests that are scheduled, but have not yet been delivered.
        """

        self.nc.removeAllDeliveredNotifications()
