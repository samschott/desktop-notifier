import platform
from unittest.mock import Mock

import pytest

from desktop_notifier import Button, Notification, ReplyField
from desktop_notifier.main import get_backend_class
from desktop_notifier.backends.dummy import DummyNotificationCenter

from .backends import (
    simulate_button_pressed,
    simulate_clicked,
    simulate_dismissed,
    simulate_replied,
)

if not platform.system() == "Darwin":
    pytest.skip("Only macOS test infra provided", allow_module_level=True)

if get_backend_class() == DummyNotificationCenter:
    pytest.skip("Dummy backend cannot handle callbacks", allow_module_level=True)


@pytest.mark.asyncio
async def test_clicked_callback_called(notifier):
    notifier.on_clicked = Mock()
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        on_clicked=Mock(),
    )
    identifier = await notifier.send_notification(notification)

    simulate_clicked(notifier, identifier)

    notifier.on_clicked.assert_not_called()
    notification.on_clicked.assert_called_once()


@pytest.mark.asyncio
async def test_dismissed_callback_called(notifier):
    notifier.on_dismissed = Mock()
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        on_dismissed=Mock(),
    )
    identifier = await notifier.send_notification(notification)

    simulate_dismissed(notifier, identifier)

    notifier.on_dismissed.assert_not_called()
    notification.on_dismissed.assert_called_once()


@pytest.mark.asyncio
async def test_button_pressed_callback_called(notifier):
    notifier.on_button_pressed = Mock()
    button1 = Button(title="Button 1", on_pressed=Mock())
    button2 = Button(title="Button 2", on_pressed=Mock())
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        buttons=[button1, button2],
    )
    identifier = await notifier.send_notification(notification)

    simulate_button_pressed(notifier, identifier, button2.identifier)

    notifier.on_button_pressed.assert_not_called()
    button2.on_pressed.assert_called_once()


@pytest.mark.asyncio
async def test_replied_callback_called(notifier):
    notifier.on_replied = Mock()
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        reply_field=ReplyField(on_replied=Mock()),
    )
    identifier = await notifier.send_notification(notification)

    simulate_replied(notifier, identifier, "A notification response")

    notifier.on_replied.assert_not_called()
    notification.reply_field.on_replied.assert_called_with("A notification response")


@pytest.mark.asyncio
async def test_clicked_fallback_handler_called(notifier):
    notifier.on_clicked = Mock()
    notification = Notification(title="Julius Caesar", message="Et tu, Brute?")
    identifier = await notifier.send_notification(notification)

    simulate_clicked(notifier, identifier)

    notifier.on_clicked.assert_called_with(identifier)


@pytest.mark.asyncio
async def test_dismissed_fallback_handler_called(notifier):
    notifier.on_dismissed = Mock()
    notification = Notification(title="Julius Caesar", message="Et tu, Brute?")
    identifier = await notifier.send_notification(notification)

    simulate_dismissed(notifier, identifier)

    notifier.on_dismissed.assert_called_with(identifier)


@pytest.mark.asyncio
async def test_button_pressed_fallback_handler_called(notifier):
    notifier.on_button_pressed = Mock()
    button1 = Button(title="Button 1")
    button2 = Button(title="Button 2")
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        buttons=[button1, button2],
    )
    identifier = await notifier.send_notification(notification)

    simulate_button_pressed(notifier, identifier, button2.identifier)

    notifier.on_button_pressed.assert_called_with(identifier, button2.identifier)


@pytest.mark.asyncio
async def test_replied_fallback_handler_called(notifier):
    notifier.on_replied = Mock()
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        reply_field=ReplyField(),
    )
    identifier = await notifier.send_notification(notification)

    simulate_replied(notifier, identifier, "A notification response")

    notifier.on_replied.assert_called_with(identifier, "A notification response")
