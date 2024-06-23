
desktop-notifier documentation
==============================

This documentation provides a short introduction to ``desktop-notifier`` and an API
reference for the main module and platform implementations.

.. toctree::
   :hidden:
   :maxdepth: 2

   background/platform_support
   background/eventloops
   background/contributing

Getting started
***************

Basic usage only requires the user to specify a notification title and message:

.. code-block:: python

    from desktop_notifier import DesktopNotifier

    notifier = DesktopNotifier()
    n = notifier.send_sync(title="Hello world!", message="Notification body")

By default, "Python" will be used as the app name for all notifications, but you can also
manually specify an app name and icon. Advanced usage also allows setting different
notification options, such as notification urgency, buttons, callbacks, etc:

.. code-block:: python

    from desktop_notifier import DesktopNotifier, Urgency, Button, ReplyField, DEFAULT_SOUND

    notifier = DesktopNotifier(
        app_name="Sample App",
        icon="file:///path/to/icon.png",
        notification_limit=10
    )

    async def main():
        await notify.send(
          title="Julius Caesar",
          message="Et tu, Brute?",
          urgency=Urgency.Critical,
          reply_field=ReplyField(
            title="Reply",
            button_title="Send",
            on_replied=lambda text: print("Brutus replied:", text),
          ),
          on_clicked=lambda: print("Notification clicked"),
          on_dismissed=lambda: print("Notification dismissed"),
          sound_file=DEFAULT_SOUND,
        )

    asyncio.run(main())

More elaborate examples can be found at
https://github.com/samschott/desktop-notifier/tree/main/examples.

Note that some platforms may not support all options. Any options or configuration
which are not supported by the platform will be silently ignored. Please refer to
:doc:`background/platform_support` for more information.

In addition to sending notifications, :class:`desktop_notifier.main.DesktopNotifier` also
provides methods to clear notifications from the platform's notification center and to
request and verify user permissions to send notifications where this is required by the
platform. Please refer to the API docs for the evolving functionality.

Synchronous API
***************

``desktop-notifier`` is a asynchronous library, designed to work with Python's asyncio.
This essential to integrate with event loops of the respective platforms and respond to
user interactions with notifications. It also simplifies usage in GUI apps where
blocking calls will cause the user interface to 'hang'.

Nevertheless, there may be some use cases where blocking is not a concern and callbacks
are not important. This might be the case for example for a daemon just sending status
updates.

For such cases, the synchronous API ``DesktopNotifierSync`` is a convenient wrapper
around ``DesktopNotifier`` to make 'regular' blocking calls.

Notes on macOS
**************

On macOS the implementation uses the ``UNUserNotificationCenter`` instead of the
deprecated ``NSUserNotificationCenter``. ``UNUserNotificationCenter`` restricts sending
desktop notifications to signed executables. This means that notifications will only
work if the Python executable or bundled app has been signed. Note that the installer
from `python.org <https://python.org>`__ provides a properly signed Python framework but
**homebrew does not** (manually signing the executable installed by homebrew _should_
work as well).

If you freeze your code with PyInstaller or a similar package, you must sign the
resulting app bundle for notifications to work. An ad-hoc signature will be sufficient
but signing with an Apple developer certificate is recommended for distribution.
