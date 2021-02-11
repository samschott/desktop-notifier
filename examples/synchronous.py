from desktop_notifier import DesktopNotifier, NotificationLevel


notifier = DesktopNotifier(
    app_name="Sample App",
    notification_limit=10,
)


notifier.send_sync(
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
