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
async def test_dispatched_callback_called(notifier: DesktopNotifier) -> None:
    class_handler = Mock()
    notification_handler = Mock()
    notifier.on_dispatched = class_handler
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        on_dispatched=notification_handler,
    )

    await notifier.send_notification(notification)

    class_handler.assert_not_called()
    notification_handler.assert_called_once()


@pytest.mark.asyncio
async def test_clicked_callback_called(notifier: DesktopNotifier) -> None:
    await check_supported(notifier, Capability.ON_CLICKED)

    class_handler = Mock()
    notification_handler = Mock()
    notifier.on_clicked = class_handler
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        on_clicked=notification_handler,
    )

    identifier = await notifier.send_notification(notification)
    simulate_clicked(notifier, identifier)

    class_handler.assert_not_called()
    notification_handler.assert_called_once()


@pytest.mark.asyncio
async def test_clicked_callback_dismissed_not_called(notifier: DesktopNotifier) -> None:
    """
    Dbus may send an on_dismissed event any time a notification is closed. Ensure that
    its callback is not triggered on different types of interactions.
    """
    await check_supported(notifier, Capability.ON_CLICKED)

    on_clicked = Mock()
    on_dismissed = Mock()
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        on_clicked=on_clicked,
        on_dismissed=on_dismissed,
    )

    identifier = await notifier.send_notification(notification)
    simulate_clicked(notifier, identifier)

    on_dismissed.assert_not_called()
    on_clicked.assert_called_once()


@pytest.mark.asyncio
async def test_dismissed_callback_called(notifier: DesktopNotifier) -> None:
    await check_supported(notifier, Capability.ON_DISMISSED)

    class_handler = Mock()
    notification_handler = Mock()
    notifier.on_dismissed = class_handler
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        on_dismissed=notification_handler,
    )

    identifier = await notifier.send_notification(notification)
    simulate_dismissed(notifier, identifier)

    class_handler.assert_not_called()
    notification_handler.assert_called_once()


@pytest.mark.asyncio
async def test_button_pressed_callback_called(notifier: DesktopNotifier) -> None:
    await check_supported(notifier, Capability.BUTTONS)

    class_handler = Mock()
    notification_b0_handler = Mock()
    notification_b1_handler = Mock()
    notifier.on_button_pressed = class_handler
    button0 = Button(title="Button 0", on_pressed=notification_b0_handler)
    button1 = Button(title="Button 1", on_pressed=notification_b1_handler)
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        buttons=(button0, button1),
    )

    identifier = await notifier.send_notification(notification)
    simulate_button_pressed(notifier, identifier, button1.identifier)

    class_handler.assert_not_called()
    notification_b1_handler.assert_called_once()


@pytest.mark.asyncio
async def test_replied_callback_called(notifier: DesktopNotifier) -> None:
    await check_supported(notifier, Capability.REPLY_FIELD)
    class_handler = Mock()
    notification_handler = Mock()

    notifier.on_replied = class_handler
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        reply_field=ReplyField(on_replied=notification_handler),
    )

    identifier = await notifier.send_notification(notification)
    simulate_replied(notifier, identifier, "A notification response")

    class_handler.assert_not_called()
    notification_handler.assert_called_with("A notification response")


@pytest.mark.asyncio
async def test_dispatched_fallback_handler_called(notifier: DesktopNotifier) -> None:
    class_handler = Mock()
    notifier.on_dispatched = class_handler
    notification = Notification(title="Julius Caesar", message="Et tu, Brute?")

    identifier = await notifier.send_notification(notification)

    class_handler.assert_called_with(identifier)


@pytest.mark.asyncio
async def test_clicked_fallback_handler_called(notifier: DesktopNotifier) -> None:
    await check_supported(notifier, Capability.ON_CLICKED)

    class_handler = Mock()
    notifier.on_clicked = class_handler
    notification = Notification(title="Julius Caesar", message="Et tu, Brute?")

    identifier = await notifier.send_notification(notification)
    simulate_clicked(notifier, identifier)

    class_handler.assert_called_with(identifier)


@pytest.mark.asyncio
async def test_dismissed_fallback_handler_called(notifier: DesktopNotifier) -> None:
    await check_supported(notifier, Capability.ON_DISMISSED)

    class_handler = Mock()
    notifier.on_dismissed = class_handler
    notification = Notification(title="Julius Caesar", message="Et tu, Brute?")

    identifier = await notifier.send_notification(notification)
    simulate_dismissed(notifier, identifier)

    class_handler.assert_called_with(identifier)


@pytest.mark.asyncio
async def test_button_pressed_fallback_handler_called(
    notifier: DesktopNotifier,
) -> None:
    await check_supported(notifier, Capability.BUTTONS)

    class_handler = Mock()
    notifier.on_button_pressed = class_handler
    button0 = Button(title="Button 1")
    button1 = Button(title="Button 2")
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        buttons=(button0, button1),
    )

    identifier = await notifier.send_notification(notification)
    simulate_button_pressed(notifier, identifier, button1.identifier)

    class_handler.assert_called_once_with(identifier, button1.identifier)


@pytest.mark.asyncio
async def test_replied_fallback_handler_called(notifier: DesktopNotifier) -> None:
    await check_supported(notifier, Capability.REPLY_FIELD)

    class_handler = Mock()
    notifier.on_replied = class_handler
    notification = Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        reply_field=ReplyField(),
    )

    identifier = await notifier.send_notification(notification)
    simulate_replied(notifier, identifier, "A notification response")

    class_handler.assert_called_with(identifier, "A notification response")
