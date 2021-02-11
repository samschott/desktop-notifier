import asyncio
import platform

from desktop_notifier import DesktopNotifier, NotificationLevel


notifier = DesktopNotifier(
    app_name="Sample App",
    notification_limit=10,
)


async def main():

    await notifier.send(
        title="Julius Caesar",
        message="Et tu, Brute?",
        urgency=NotificationLevel.Critical,
        buttons={"Mark as read": lambda: print("Marked as read")},
        reply_field=True,
        on_replied=lambda text: print("Brutus replied:", text),
        on_clicked=lambda: print("Notification clicked"),
        on_dismissed=lambda: print("Notification dismissed"),
        sound=True,
    )


if platform.system() == "Darwin":
    from rubicon.objc.eventloop import EventLoopPolicy

    asyncio.set_event_loop_policy(EventLoopPolicy())

loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
