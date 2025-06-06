import asyncio
import platform
import signal

from desktop_notifier import DEFAULT_SOUND, Button, DesktopNotifier, ReplyField, Urgency

# Integrate with Core Foundation event loop on macOS to allow receiving callbacks.
if platform.system() == "Darwin":
    from rubicon.objc.eventloop import EventLoopPolicy

    asyncio.set_event_loop_policy(EventLoopPolicy())


async def main() -> None:
    notifier = DesktopNotifier(app_name="Sample App")

    await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
        urgency=Urgency.Critical,
        buttons=[
            Button(
                title="Mark as read",
                on_pressed=lambda: print("Button 'Mark as read' was clicked"),
            ),
            Button(
                title="Click me!!",
                on_pressed=lambda: print("Button 'Click me!!' was clicked"),
            ),
        ],
        reply_field=ReplyField(
            title="Reply",
            button_title="Send",
            on_replied=lambda text: print(f"Received reply '{text}'"),
        ),
        on_dispatched=lambda: print("Notification is showing now"),
        on_clicked=lambda: print("Notification was clicked"),
        on_dismissed=lambda: print("Notification was dismissed"),
        sound=DEFAULT_SOUND,
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
