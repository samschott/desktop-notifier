import asyncio
import platform
import signal

from desktop_notifier import DEFAULT_SOUND, Button, DesktopNotifier, ReplyField, Urgency

# Integrate with Core Foundation event loop on macOS to allow receiving callbacks.
if platform.system() == "Darwin":
    from rubicon.objc.eventloop import EventLoopPolicy

    asyncio.set_event_loop_policy(EventLoopPolicy())


def on_dispatched(identifier: str) -> None:
    print(f"Notification '{identifier}' is showing now")


def on_cleared(identifier: str) -> None:
    print(f"Notification '{identifier}' was cleared without user interaction")


def on_clicked(identifier: str) -> None:
    print(f"Notification '{identifier}' was clicked")


def on_dismissed(identifier: str) -> None:
    print(f"Notification '{identifier}' was dismissed")


def on_button_pressed(identifier: str, button_identifier: str) -> None:
    print(f"Button '{button_identifier}' on notification '{identifier}' was clicked")


def on_replied(identifier: str, reply: str) -> None:
    print(f"Received reply '{reply}' from notification '{identifier}'")


async def main() -> None:
    notifier = DesktopNotifier(app_name="Sample App")
    notifier.on_dispatched = on_dispatched
    notifier.on_cleared = on_cleared
    notifier.on_clicked = on_clicked
    notifier.on_dismissed = on_dismissed
    notifier.on_button_pressed = on_button_pressed
    notifier.on_replied = on_replied

    await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
        urgency=Urgency.Critical,
        buttons=[
            Button(title="Mark as read", identifier="MARK_AS_READ"),
            Button(title="Click me!!", identifier="CLICK_ME"),
        ],
        reply_field=ReplyField(
            title="Reply",
            button_title="Send",
        ),
        sound=DEFAULT_SOUND,
        timeout=10,
    )

    # Run the event loop forever to respond to user interactions with the notification.
    event = asyncio.Event()

    if platform.system() != "Windows":
        # Handle SIGINT and SIGTERM gracefully on Unix.
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, event.set)
        loop.add_signal_handler(signal.SIGTERM, event.set)

    await event.wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle KeyboardInterrupt gracefully on Windows.
        pass
