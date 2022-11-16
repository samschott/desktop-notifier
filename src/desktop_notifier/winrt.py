# -*- coding: utf-8 -*-
"""
Notification backend for Windows. Unlike other platforms, sending rich "toast"
notifications cannot be done via FFI / ctypes because the C winapi only supports basic
notifications with a title and message. This backend therefore requires interaction with
the Windows Runtime and uses the winrt package with compiled components published by
Microsoft (https://github.com/microsoft/xlang, https://pypi.org/project/winrt/).
"""

# system imports
import uuid
import logging
from xml.etree.ElementTree import Element, SubElement, tostring
from typing import Optional, TypeVar, cast

# external imports
from winsdk.windows.ui.notifications import (
    ToastNotificationManager,
    ToastNotificationPriority,
    NotificationSetting,
    ToastNotification,
    ToastActivatedEventArgs,
    ToastDismissalReason,
)
from winsdk.windows.data.xml import dom
from winsdk.windows.applicationmodel.core import CoreApplication
from winsdk.windows.applicationmodel.background import (
    BackgroundTaskRegistration,
    BackgroundTaskBuilder,
    BackgroundExecutionManager,
    BackgroundAccessStatus,
    ToastNotificationActionTrigger,
)
from winsdk.windows.foundation import IPropertyValue, PropertyType

# local imports
from .base import Notification, DesktopNotifierBase, Urgency


__all__ = ["WinRTDesktopNotifier"]

logger = logging.getLogger(__name__)

T = TypeVar("T")


class WinRTDesktopNotifier(DesktopNotifierBase):
    """Notification backend for the Windows Runtime

    :param app_name: The name of the app. This has no effect since the app name will be
        automatically determined.
    :param app_icon: The default icon to use for notifications. This has no effect since
        the app icon will be automatically determined.
    :param notification_limit: Maximum number of notifications to keep in the system's
        notification center.
    """

    _to_native_urgency = {
        Urgency.Low: ToastNotificationPriority.DEFAULT,
        Urgency.Normal: ToastNotificationPriority.DEFAULT,
        Urgency.Critical: ToastNotificationPriority.HIGH,
    }

    background_task_name = "DesktopNotifier-ToastBackgroundTask"

    def __init__(
        self,
        app_name: str = "Python",
        app_icon: Optional[str] = None,
        notification_limit: Optional[int] = None,
    ) -> None:
        super().__init__(app_name, app_icon, notification_limit)
        self._appid = CoreApplication.get_id()
        self.manager = ToastNotificationManager.get_default()
        self.notifier = self.manager.create_toast_notifier(self._appid)

    async def request_authorisation(self) -> bool:
        """
        Request authorisation to send notifications.

        :returns: Whether authorisation has been granted.
        """
        if not await self._request_background_task_access():
            return False
        return await self.has_authorisation()

    async def has_authorisation(self) -> bool:
        """
        Whether we have authorisation to send notifications.
        """
        return (
            self.notifier.setting == NotificationSetting.ENABLED
            and await self._has_background_task_access()
        )

    async def _has_background_task_access(self) -> bool:
        res = await BackgroundExecutionManager.request_access_async(self._appid)
        return res not in {
            BackgroundAccessStatus.DENIED_BY_SYSTEM_POLICY,
            BackgroundAccessStatus.DENIED_BY_USER,
        }

    def _has_registered_background_task(self) -> bool:
        tasks = BackgroundTaskRegistration.get_all_tasks()
        return any(t.name == self.background_task_name for t in tasks.values())

    async def _request_background_task_access(self) -> bool:
        """Request permission to activate in the background."""
        if self._appid == "":
            logger.warning(
                "Only applications can send desktop notifications. "
                "Could not find App ID for process."
            )
            return False

        if not await self._has_background_task_access():
            logger.warning("This app is not allowed to run background tasks.")
            return False

        # If background task is already registered, do nothing.
        if self._has_registered_background_task():
            return True

        # Create the background tasks.
        builder = BackgroundTaskBuilder()
        builder.name = self.background_task_name

        builder.set_trigger(ToastNotificationActionTrigger())
        builder.register()

        return True

    async def _send(
        self,
        notification: Notification,
        notification_to_replace: Optional[Notification],
    ) -> str:
        """
        Asynchronously sends a notification.

        :param notification: Notification to send.
        :param notification_to_replace: Notification to replace, if any.
        """

        if notification_to_replace:
            platform_nid = cast(str, notification_to_replace.identifier)
        else:
            platform_nid = str(uuid.uuid4())

        # Create notification XML.
        toast_xml = Element("toast", {"launch": "default"})
        visual_xml = SubElement(toast_xml, "visual")
        actions_xml = SubElement(toast_xml, "actions")

        if notification.thread:
            SubElement(
                toast_xml,
                "header",
                {"id": notification.thread, "title": notification.thread},
            )

        binding = SubElement(visual_xml, "binding", {"template": "ToastGeneric"})

        title_xml = SubElement(binding, "text")
        title_xml.text = notification.title

        message_xml = SubElement(binding, "text")
        message_xml.text = notification.message

        if notification.icon:
            SubElement(
                binding,
                "image",
                {"placement": "appLogoOverride", "src": notification.icon},
            )

        if notification.attachment:
            SubElement(
                binding, "image", {"placement": "hero", "src": notification.attachment}
            )

        if notification.reply_field:
            SubElement(actions_xml, "input", {"id": "textBox", "type": "text"})
            reply_button_xml = SubElement(
                actions_xml,
                "action",
                {
                    "content": notification.reply_field.button_title,
                    "activationType": "background",
                    "arguments": "action=reply&amp",
                },
            )

            # If there are no other buttons, show the
            # reply buttons next to the text field.
            if not notification.buttons:
                reply_button_xml.set("hint-inputId", "textBox")

        for n, button in enumerate(notification.buttons):
            SubElement(
                actions_xml,
                "action",
                {
                    "content": button.title,
                    "activationType": "background",
                    "arguments": str(n),
                },
            )

        if notification.sound:
            SubElement(
                toast_xml, "audio", {"src": "ms-winsoundevent:Notification.Default"}
            )
        else:
            SubElement(toast_xml, "audio", {"silent": "true"})

        xml_document = dom.XmlDocument()
        xml_document.load_xml(tostring(toast_xml, encoding="unicode"))

        native = ToastNotification(xml_document)
        native.tag = platform_nid
        native.priority = self._to_native_urgency[notification.urgency]

        if notification.thread:
            native.group = notification.thread
        else:
            native.group = "default"

        def on_activated(sender, boxed_activated_args):
            activated_args = ToastActivatedEventArgs._from(boxed_activated_args)
            action_id = cast(str, activated_args.arguments)

            if action_id == "default":
                if notification.on_clicked:
                    notification.on_clicked()

            elif action_id == "action=reply&amp":
                if notification.reply_field.on_replied:
                    boxed_text = activated_args.user_input["textBox"]
                    text = unbox_winrt(boxed_text)
                    notification.reply_field.on_replied(text)

            elif action_id.isnumeric():
                action_number = int(action_id)
                notification.buttons[action_number].on_pressed()

        def on_dismissed(sender, dismissed_args):

            self._clear_notification_from_cache(notification)

            if dismissed_args.reason == ToastDismissalReason.USER_CANCELED:
                if notification.on_dismissed:
                    notification.on_dismissed()

        def on_failed(sender, failed_args):
            logger.warning(
                f"Notification failed (error code {failed_args.error_code.value})"
            )

        native.add_activated(on_activated)
        native.add_dismissed(on_dismissed)
        native.add_failed(on_failed)

        self.notifier.show(native)

        return platform_nid

    async def _clear(self, notification: Notification) -> None:
        """c
        Asynchronously removes a notification from the notification center.
        """
        group = notification.thread or "default"
        self.manager.history.remove(notification.identifier, group, self._appid)

    async def _clear_all(self) -> None:
        """
        Asynchronously clears all notifications from notification center.
        """
        self.manager.history.clear(self._appid)


def unbox_winrt(boxed_value):
    """
    Unbox winrt object. See https://github.com/pywinrt/pywinrt/issues/8.
    """
    if boxed_value is None:
        return boxed_value

    value = IPropertyValue._from(boxed_value)

    if value.type is PropertyType.EMPTY:
        return None
    elif value.type is PropertyType.UINT8:
        return value.get_uint8()
    elif value.type is PropertyType.INT16:
        return value.get_int16()
    elif value.type is PropertyType.UINT16:
        return value.get_uint16()
    elif value.type is PropertyType.STRING:
        return value.get_string()
    else:
        raise NotImplementedError(f"Unboxing {value.type} is not yet supported")
