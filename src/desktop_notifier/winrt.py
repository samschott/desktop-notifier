# -*- coding: utf-8 -*-
"""
Notification backend for Windows

Unlike other platforms, sending rich "toast" notifications cannot be done via FFI /
ctypes because the C winapi only supports basic notifications with a title and message.
This backend therefore requires interaction with the Windows Runtime and uses the winrt
package with compiled components.
"""

from __future__ import annotations

# system imports
import sys
import uuid
import logging
from xml.etree.ElementTree import Element, SubElement, tostring
from typing import TypeVar

# external imports
import winreg
from winrt.windows.foundation.interop import unbox
from winrt.windows.ui.notifications import (
    ToastNotificationManager,
    ToastNotificationPriority,
    NotificationSetting,
    ToastNotification,
    ToastActivatedEventArgs,
    ToastDismissalReason,
    ToastDismissedEventArgs,
    ToastFailedEventArgs,
)
from winrt.windows.data.xml.dom import XmlDocument
from winrt.windows.applicationmodel.core import CoreApplication
from winrt.system import Object as WinRTObject

# local imports
from .base import Notification, DesktopNotifierBase, Urgency, Capability, DEFAULT_SOUND


__all__ = ["WinRTDesktopNotifier"]

logger = logging.getLogger(__name__)

T = TypeVar("T")


def register_hkey(app_id: str, app_name: str) -> None:
    # mypy type guard
    if not sys.platform == "win32":
        return

    winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    key_path = f"SOFTWARE\\Classes\\AppUserModelId\\{app_id}"
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path) as master_key:
        winreg.SetValueEx(master_key, "DisplayName", 0, winreg.REG_SZ, app_name)


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

        manager = ToastNotificationManager.get_default()

        if not manager:
            raise RuntimeError("Could not get ToastNotificationManagerForUser")

        self.manager = manager

        # Prefer using the real App ID if detected, fall back to user-provided name
        # and icon otherwise.
        if CoreApplication.id != "":
            self.app_id = CoreApplication.id
        else:
            self.app_id = app_name
            register_hkey(app_id=app_name, app_name=app_name)

        notifier = self.manager.create_toast_notifier(self.app_id)

        if not notifier:
            raise RuntimeError(f"Could not get ToastNotifier for app_id: {self.app_id}")

        self.notifier = notifier

    async def request_authorisation(self) -> bool:
        """
        Request authorisation to send notifications.

        :returns: Whether authorisation has been granted.
        """
        return await self.has_authorisation()

    async def has_authorisation(self) -> bool:
        """
        Whether we have authorisation to send notifications.
        """
        try:
            return bool(self.notifier.setting == NotificationSetting.ENABLED)
        except OSError:
            # See https://github.com/samschott/desktop-notifier/issues/95.
            return True

    async def _send(
        self,
        notification: Notification,
        notification_to_replace: Notification | None,
    ) -> None:
        """
        Asynchronously sends a notification.

        :param notification: Notification to send.
        :param notification_to_replace: Notification to replace, if any.
        """
        if notification_to_replace:
            platform_nid = notification_to_replace.identifier
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

        if notification.icon and notification.icon.is_file():
            SubElement(
                binding,
                "image",
                {
                    "placement": "appLogoOverride",
                    "src": notification.icon.as_uri(),
                },
            )

        if notification.attachment:
            SubElement(
                binding,
                "image",
                {"placement": "hero", "src": notification.attachment.as_uri()},
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
            if notification.sound == DEFAULT_SOUND:
                sound_attr = {"src": "ms-winsoundevent:Notification.Default"}
            elif notification.sound.name:
                sound_attr = {"src": notification.sound.name}
            else:
                sound_attr = {"src": notification.sound.as_uri()}
        else:
            sound_attr = {"silent": "true"}

        SubElement(toast_xml, "audio", sound_attr)

        xml_document = XmlDocument()
        xml_document.load_xml(tostring(toast_xml, encoding="unicode"))

        native = ToastNotification(xml_document)
        native.tag = platform_nid
        native.priority = self._to_native_urgency[notification.urgency]

        def on_activated(
            sender: ToastNotification | None, boxed_activated_args: WinRTObject | None
        ) -> None:
            if not sender or not boxed_activated_args:
                return

            try:
                activated_args = ToastActivatedEventArgs._from(boxed_activated_args)
            except Exception:
                return

            action_id = activated_args.arguments

            if action_id == WinRTDesktopNotifier.DEFAULT_ACTION:
                if notification.on_clicked:
                    notification.on_clicked()
            elif action_id == WinRTDesktopNotifier.REPLY_ACTION:
                if (
                    notification.reply_field
                    and notification.reply_field.on_replied
                    and activated_args.user_input
                ):
                    boxed_text = activated_args.user_input[
                        WinRTDesktopNotifier.REPLY_TEXTBOX_NAME
                    ]
                    text = unbox(boxed_text)
                    notification.reply_field.on_replied(text)
            elif action_id.startswith(WinRTDesktopNotifier.BUTTON_ACTION_PREFIX):
                action_number_str = action_id.replace(
                    WinRTDesktopNotifier.BUTTON_ACTION_PREFIX, ""
                )
                action_number = int(action_number_str)
                callback = notification.buttons[action_number].on_pressed
                if callback:
                    callback()

        def on_dismissed(
            sender: ToastNotification | None,
            dismissed_args: ToastDismissedEventArgs | None,
        ) -> None:
            self._clear_notification_from_cache(notification)

            if (
                dismissed_args
                and dismissed_args.reason == ToastDismissalReason.USER_CANCELED
            ):
                if notification.on_dismissed:
                    notification.on_dismissed()

        def on_failed(
            sender: ToastNotification | None, failed_args: ToastFailedEventArgs | None
        ) -> None:
            if failed_args:
                logger.warning(
                    f"Notification failed (error code {failed_args.error_code.value})"
                )
            else:
                logger.warning("Notification failed (unknown error code)")

        native.add_activated(on_activated)
        native.add_dismissed(on_dismissed)
        native.add_failed(on_failed)

        self.notifier.show(native)

        notification.identifier = platform_nid

    async def _clear(self, notification: Notification) -> None:
        """
        Asynchronously removes a notification from the notification center.
        """
        if self.manager.history:
            self.manager.history.remove(notification.identifier)

    async def _clear_all(self) -> None:
        """
        Asynchronously clears all notifications from notification center.
        """
        if self.manager.history:
            self.manager.history.clear(self.app_id)

    async def get_capabilities(self) -> frozenset[Capability]:
        capabilities = {
            Capability.TITLE,
            Capability.MESSAGE,
            Capability.ICON,
            Capability.BUTTONS,
            Capability.REPLY_FIELD,
            Capability.ON_CLICKED,
            Capability.ON_DISMISSED,
            Capability.THREAD,
            Capability.ATTACHMENT,
            Capability.SOUND,
            Capability.SOUND_NAME,
        }
        # Custom audio is support only starting with the Windows 10 Anniversary update.
        # See https://learn.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/custom-audio-on-toasts#add-the-custom-audio.
        if sys.getwindowsversion().build >= 1607:  # type:ignore[attr-defined]
            capabilities.add(Capability.SOUND_FILE)

        return frozenset(capabilities)
