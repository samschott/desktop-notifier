# -*- coding: utf-8 -*-
"""
Notification backend for Windows. Unlike other platforms, sending rich "toast"
notifications cannot be done via FFI / ctypes because the C winapi only supports basic
notifications with a title and message. This backend therefore requires interaction with
the Windows Runtime and uses the winrt package with compiled components published by
Microsoft (https://github.com/microsoft/xlang, https://pypi.org/project/winrt/).
"""

from __future__ import annotations

# system imports
import uuid
import logging
from xml.etree.ElementTree import Element, SubElement, tostring
from typing import TypeVar, Any, cast

# external imports
import winreg
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
from winsdk.windows.foundation import IPropertyValue, PropertyType
import winsdk._winrt as _winrt

# local imports
from .base import Notification, DesktopNotifierBase, Urgency


__all__ = ["WinRTDesktopNotifier"]

logger = logging.getLogger(__name__)

T = TypeVar("T")


def register_hkey(app_id: str, app_name: str) -> None:
    winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)  # type:ignore
    key_path = f"SOFTWARE\\Classes\\AppUserModelId\\{app_id}"
    with winreg.CreateKeyEx(  # type:ignore
        winreg.HKEY_CURRENT_USER, key_path  # type:ignore
    ) as master_key:
        winreg.SetValueEx(  # type:ignore
            master_key, "DisplayName", 0, winreg.REG_SZ, app_name  # type:ignore
        )


class WinRTDesktopNotifier(DesktopNotifierBase):
    """Notification backend for the Windows Runtime

    :param app_name: The name of the app. This has no effect since the app name will be
        automatically determined.
    :param notification_limit: Maximum number of notifications to keep in the system's
        notification center.
    """

    _to_native_urgency = {
        Urgency.Low: ToastNotificationPriority.DEFAULT,
        Urgency.Normal: ToastNotificationPriority.DEFAULT,
        Urgency.Critical: ToastNotificationPriority.HIGH,
    }

    DEFAULT_ACTION = "default"
    REPLY_ACTION = "action=reply&amp"
    BUTTON_ACTION_PREFIX = "action=button&amp;id="
    REPLY_TEXTBOX_NAME = "textBox"

    def __init__(
        self,
        app_name: str = "Python",
        notification_limit: int | None = None,
    ) -> None:
        super().__init__(app_name, notification_limit)
        self.manager = ToastNotificationManager.get_default()

        # Prefer using the real App ID if detected, fall back to user-provided name
        # and icon otherwise.
        if CoreApplication.id != "":
            self.app_id = CoreApplication.id
        else:
            self.app_id = app_name
            register_hkey(app_name, app_name)
        self.notifier = self.manager.create_toast_notifier(self.app_id)

    async def request_authorisation(self) -> bool:
        """
        Request authorisation to send notifications.

        :returns: Whether authorisation has been granted.
        """
        return bool(self.notifier.setting == NotificationSetting.ENABLED)

    async def has_authorisation(self) -> bool:
        """
        Whether we have authorisation to send notifications.
        """
        return bool(self.notifier.setting == NotificationSetting.ENABLED)

    async def _send(
        self,
        notification: Notification,
        notification_to_replace: Notification | None,
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
        toast_xml = Element("toast", {"launch": WinRTDesktopNotifier.DEFAULT_ACTION})
        visual_xml = SubElement(toast_xml, "visual")
        actions_xml = SubElement(toast_xml, "actions")

        if notification.thread:
            SubElement(
                toast_xml,
                "header",
                {
                    "id": notification.thread,
                    "title": notification.thread,
                    "arguments": WinRTDesktopNotifier.DEFAULT_ACTION,
                    "activationType": "background",
                },
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
            SubElement(
                actions_xml,
                "input",
                {"id": WinRTDesktopNotifier.REPLY_TEXTBOX_NAME, "type": "text"},
            )
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
                reply_button_xml.set(
                    "hint-inputId", WinRTDesktopNotifier.REPLY_TEXTBOX_NAME
                )

        for n, button in enumerate(notification.buttons):
            SubElement(
                actions_xml,
                "action",
                {
                    "content": button.title,
                    "activationType": "background",
                    "arguments": WinRTDesktopNotifier.BUTTON_ACTION_PREFIX + str(n),
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

        def on_activated(sender, boxed_activated_args) -> None:  # type:ignore
            activated_args = ToastActivatedEventArgs._from(boxed_activated_args)
            action_id = cast(str, activated_args.arguments)

            if action_id == WinRTDesktopNotifier.DEFAULT_ACTION:
                if notification.on_clicked:
                    notification.on_clicked()
            elif action_id == WinRTDesktopNotifier.REPLY_ACTION:
                if notification.reply_field and notification.reply_field.on_replied:
                    boxed_text = activated_args.user_input[
                        WinRTDesktopNotifier.REPLY_TEXTBOX_NAME
                    ]
                    text = unbox_winrt(boxed_text)
                    notification.reply_field.on_replied(text)
            elif action_id.startswith(WinRTDesktopNotifier.BUTTON_ACTION_PREFIX):
                action_number_str = action_id.replace(
                    WinRTDesktopNotifier.BUTTON_ACTION_PREFIX, ""
                )
                action_number = int(action_number_str)
                callback = notification.buttons[action_number].on_pressed
                if callback:
                    callback()

        def on_dismissed(sender, dismissed_args) -> None:  # type:ignore
            self._clear_notification_from_cache(notification)

            if dismissed_args.reason == ToastDismissalReason.USER_CANCELED:
                if notification.on_dismissed:
                    notification.on_dismissed()

        def on_failed(sender, failed_args) -> None:  # type:ignore
            logger.warning(
                f"Notification failed (error code {failed_args.error_code.value})"
            )

        native.add_activated(on_activated)
        native.add_dismissed(on_dismissed)
        native.add_failed(on_failed)

        self.notifier.show(native)

        return platform_nid

    async def _clear(self, notification: Notification) -> None:
        """
        Asynchronously removes a notification from the notification center.
        """
        self.manager.history.remove(notification.identifier)

    async def _clear_all(self) -> None:
        """
        Asynchronously clears all notifications from notification center.
        """
        self.manager.history.clear(self.app_id)


def unbox_winrt(boxed_value: _winrt.Object) -> Any:
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
