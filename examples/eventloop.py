import asyncio
import platform

from desktop_notifier import DesktopNotifier, Urgency, Button, ReplyField, DEFAULT_SOUND


notify = DesktopNotifier(
    app_name="Sample App",
    notification_limit=10,
)


async def main() -> None:

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

    asyncio.run(main())
