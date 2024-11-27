from desktop_notifier import (
    DEFAULT_SOUND,
    Button,
    DesktopNotifierSync,
    ReplyField,
    Urgency,
)

notifier = DesktopNotifierSync(app_name="Sample App")

notifier.send(
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
    on_cleared=lambda: print("Notification timed out"),
    on_clicked=lambda: print("Notification clicked"),
    on_dismissed=lambda: print("Notification dismissed"),
    sound=DEFAULT_SOUND,
    timeout=10,
)
