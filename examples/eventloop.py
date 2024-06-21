import asyncio
import platform
import signal

from desktop_notifier import DesktopNotifier, Urgency, Button, ReplyField, DEFAULT_SOUND


notify = DesktopNotifier(
    app_name="Sample App",
    notification_limit=10,
)


async def main() -> None:
    loop = asyncio.get_running_loop()

    def stop_loop(loop: asyncio.AbstractEventLoop) -> None:
        loop.stop()

    loop.add_signal_handler(signal.SIGINT, stop_loop, loop)
    loop.add_signal_handler(signal.SIGTERM, stop_loop, loop)

    await notify.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
        urgency=Urgency.Critical,
        buttons=[
            Button(
                title="Mark as read",
                on_pressed=lambda: print("Marked as read"),
            )
        ],
        reply_field=ReplyField(
            title="Reply",
            button_title="Send",
            on_replied=lambda text: print("Brutus replied:", text),
        ),
        on_clicked=lambda: print("Notification clicked"),
        on_dismissed=lambda: print("Notification dismissed"),
        sound=DEFAULT_SOUND,
    )


if __name__ == "__main__":
    if platform.system() == "Darwin":
        from rubicon.objc.eventloop import EventLoopPolicy

        asyncio.set_event_loop_policy(EventLoopPolicy())

    # Run the event loop forever to respond to user interactions with the notification.
    # Otherwise, a simpler `asyncio.run(main())` call would work as well.
    loop = asyncio.new_event_loop()
    loop.create_task(main())
    loop.run_forever()
