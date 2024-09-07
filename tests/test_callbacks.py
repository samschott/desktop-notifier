import platform
from unittest.mock import Mock

import pytest

from desktop_notifier import (
    Button,
    Capability,
    DesktopNotifier,
    Notification,
    ReplyField,
)

from .backends import (
    simulate_button_pressed,
    simulate_clicked,
    simulate_dismissed,
    simulate_replied,
)

if platform.system() == "Windows":
    pytest.skip("Windows test infra missing", allow_module_level=True)


async def check_supported(notifier: DesktopNotifier, capability: Capability) -> None:
    capabilities = await notifier.get_capabilities()
    if capability not in capabilities:
        pytest.skip(f"{notifier} not supported by backend")


@pytest.mark.asyncio
async def test_clicked_callback_called(notifier):
    await check_supported(notifier, Capability.ON_CLICKED)

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
async def test_clicked_callback_dismissed_not_called(notifier):
    """
    Dbus may send an on_dismissed event any time a notification is closed. Ensure that
    its callback is not tiggered on different types of interactions.
    """
    await check_supported(notifier, Capability.ON_CLICKED)

    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        on_clicked=Mock(),
        on_dismissed=Mock(),
    )
    identifier = await notifier.send_notification(notification)

    simulate_clicked(notifier, identifier)

    notification.on_dismissed.assert_not_called()
    notification.on_clicked.assert_called_once()


@pytest.mark.asyncio
async def test_dismissed_callback_called(notifier):
    await check_supported(notifier, Capability.ON_DISMISSED)

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
    await check_supported(notifier, Capability.BUTTONS)

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
    await check_supported(notifier, Capability.REPLY_FIELD)

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
    await check_supported(notifier, Capability.ON_CLICKED)

    notifier.on_clicked = Mock()
    notification = Notification(title="Julius Caesar", message="Et tu, Brute?")
    identifier = await notifier.send_notification(notification)

    simulate_clicked(notifier, identifier)

    notifier.on_clicked.assert_called_with(identifier)


@pytest.mark.asyncio
async def test_dismissed_fallback_handler_called(notifier):
    await check_supported(notifier, Capability.ON_DISMISSED)

    notifier.on_dismissed = Mock()
    notification = Notification(title="Julius Caesar", message="Et tu, Brute?")
    identifier = await notifier.send_notification(notification)

    simulate_dismissed(notifier, identifier)

    notifier.on_dismissed.assert_called_with(identifier)


@pytest.mark.asyncio
async def test_button_pressed_fallback_handler_called(notifier):
    await check_supported(notifier, Capability.BUTTONS)

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
    await check_supported(notifier, Capability.REPLY_FIELD)

    notifier.on_replied = Mock()
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        reply_field=ReplyField(),
    )
    identifier = await notifier.send_notification(notification)

    simulate_replied(notifier, identifier, "A notification response")

    notifier.on_replied.assert_called_with(identifier, "A notification response")
