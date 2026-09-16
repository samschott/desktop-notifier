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
    on_cleared=lambda: print("Notification was closed w/o user interaction"),
    on_clicked=lambda: print("Notification was clicked"),
    on_dismissed=lambda: print("Notification was dismissed by the user"),
    sound=DEFAULT_SOUND,
)
