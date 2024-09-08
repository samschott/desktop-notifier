# -*- coding: utf-8 -*-
"""
Notification backend for Windows

Unlike other platforms, sending rich "toast" notifications cannot be done via FFI /
ctypes because the C winapi only supports basic notifications with a title and message.
This backend therefore requires interaction with the Windows Runtime and uses the winrt
package with compiled components.
"""
from __future__ import annotations

import logging
import sys
import winreg
from typing import TypeVar
from xml.etree.ElementTree import Element, SubElement, tostring

from winrt.system import Object as WinRTObject
from winrt.windows.applicationmodel.core import CoreApplication
from winrt.windows.data.xml.dom import XmlDocument
from winrt.windows.foundation.interop import unbox
from winrt.windows.ui.notifications import (
    NotificationSetting,
    ToastActivatedEventArgs,
    ToastDismissalReason,
    ToastDismissedEventArgs,
    ToastFailedEventArgs,
    ToastNotification,
    ToastNotificationManager,
    ToastNotificationPriority,
)

# local imports
from ..common import DEFAULT_SOUND, Capability, Notification, Urgency
from .base import DesktopNotifierBackend

__all__ = ["WinRTDesktopNotifier"]

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_ACTION = "default"
REPLY_ACTION = "action=reply&amp"
BUTTON_ACTION_PREFIX = "action=button&amp;id="
REPLY_TEXTBOX_NAME = "textBox"


def register_hkey(app_id: str, app_name: str) -> None:
    # mypy type guard
    if not sys.platform == "win32":
        return

    winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    key_path = f"SOFTWARE\\Classes\\AppUserModelId\\{app_id}"
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path) as master_key:
        winreg.SetValueEx(master_key, "DisplayName", 0, winreg.REG_SZ, app_name)


class WinRTDesktopNotifier(DesktopNotifierBackend):
    """Notification backend for the Windows Runtime

    :param app_name: The name of the app.
    """

    _to_native_urgency = {
        Urgency.Low: ToastNotificationPriority.DEFAULT,
        Urgency.Normal: ToastNotificationPriority.DEFAULT,
        Urgency.Critical: ToastNotificationPriority.HIGH,
    }

    def __init__(
        self,
        app_name: str,
    ) -> None:
        super().__init__(app_name)

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

    async def _send(self, notification: Notification) -> None:
        """
        Asynchronously sends a notification.

        :param notification: Notification to send.
        """
        toast_xml = Element("toast", {"launch": DEFAULT_ACTION})
        visual_xml = SubElement(toast_xml, "visual")
        actions_xml = SubElement(toast_xml, "actions")

        if notification.thread:
            SubElement(
                toast_xml,
                "header",
                {
                    "id": notification.thread,
                    "title": notification.thread,
                    "arguments": DEFAULT_ACTION,
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
                {"id": REPLY_TEXTBOX_NAME, "type": "text"},
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

            # If there are no other buttons, show the reply button next to the text
            # field. Otherwise, show it above other buttons.
            if not notification.buttons:
                reply_button_xml.set("hint-inputId", REPLY_TEXTBOX_NAME)

        for button in notification.buttons:
            SubElement(
                actions_xml,
                "action",
                {
                    "content": button.title,
                    "activationType": "background",
                    "arguments": BUTTON_ACTION_PREFIX + button.identifier,
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
        native.tag = notification.identifier
        native.priority = self._to_native_urgency[notification.urgency]

        native.add_activated(self._on_activated)
        native.add_dismissed(self._on_dismissed)
        native.add_failed(self._on_failed)

        self.notifier.show(native)

    def _on_activated(
        self, sender: ToastNotification | None, boxed_activated_args: WinRTObject | None
    ) -> None:
        if not sender:
            return

        notification = self._clear_notification_from_cache(sender.tag)

        if not boxed_activated_args:
            return

        activated_args = ToastActivatedEventArgs._from(boxed_activated_args)
        action_id = activated_args.arguments

        if action_id == DEFAULT_ACTION:
            self.handle_clicked(sender.tag, notification)

        elif action_id == REPLY_ACTION and activated_args.user_input:
            boxed_reply = activated_args.user_input[REPLY_TEXTBOX_NAME]
            reply = unbox(boxed_reply)
            self.handle_replied(sender.tag, reply, notification)

        elif action_id.startswith(BUTTON_ACTION_PREFIX):
            button_id = action_id.replace(BUTTON_ACTION_PREFIX, "")
            self.handle_button(sender.tag, button_id, notification)

    def _on_dismissed(
        self,
        sender: ToastNotification | None,
        dismissed_args: ToastDismissedEventArgs | None,
    ) -> None:
        if not sender:
            return

        notification = self._clear_notification_from_cache(sender.tag)

        if (
            dismissed_args
            and dismissed_args.reason == ToastDismissalReason.USER_CANCELED
        ):
            self.handle_dismissed(sender.tag, notification)

    def _on_failed(
        self, sender: ToastNotification | None, failed_args: ToastFailedEventArgs | None
    ) -> None:
        if not sender:
            return

        self._clear_notification_from_cache(sender.tag)
        if failed_args:
            logger.warning(
                "Notification '%s' failed with error code %s",
                sender.tag,
                failed_args.error_code.value,
            )
        else:
            logger.warning("Notification '%s' failed with unknown error", sender.tag)

    async def _clear(self, identifier: str) -> None:
        """
        Asynchronously removes a notification from the notification center.
        """
        if self.manager.history:
            self.manager.history.remove(identifier)

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
