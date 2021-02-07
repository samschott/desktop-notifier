
desktop-notifier documentation
==============================

This documentation provides a short introduction to ``desktop-notifier`` and an API
reference for the main module and platform implementations.

.. toctree::
   :hidden:
   :caption: Background
   :maxdepth: 2

   background/platform_support
   background/contributing

.. toctree::
   :hidden:
   :caption: Reference
   :maxdepth: 2

   autoapi/desktop_notifier/main/index
   autoapi/desktop_notifier/base/main
   autoapi/desktop_notifier/macos/index
   autoapi/desktop_notifier/macos_legacy/index
   autoapi/desktop_notifier/dbus/index
   autoapi/desktop_notifier/dummy/index

Getting started
***************

Basic usage only requires the user to specify a notification title and message:

.. code-block:: python

    from desktop_notifier import DesktopNotifier

    notifier = DesktopNotifier()
    n = notifier.send(title="Hello world!", message="Notification body")

    notifier.clear(n)  # removes the notification from the notification center
    notifier.clear_all()  # removes all notifications for this app

By default, "Python" will be used as the app name for all notifications, but you can also
manually specify an app name and icon. Advanced usage also allows setting different
notification options, such as notification urgency, buttons, callbacks, etc:

.. code-block:: python

    from desktop_notifier import DesktopNotifier, NotificationLevel

    notifier = DesktopNotifier(
        app_name="Sample App",
        icon="file:///path/to/icon.png",
        notification_limit=10
    )

    notifier.send(
        title="Hello from Python!",
        message="A horrible exception occured",
        urgency=NotificationLevel.Critical,
        action=lambda: print("notification clicked"),
        buttons={
            "Button 1": lambda: print("Button 1 clicked"),
            "Button 2": lambda: print("Button 2 clicked"),
        },
        sound=True,
    )

Note that some platforms may not support all options. Any options or configuration
which are not supported by the platform will be silently ignored. Please refer to
:ref:`background/platform_support` for more information.


Execution of callbacks requires a running event loop. On Linux, it requires a running
`asyncio <https://docs.python.org/3/library/asyncio.html>`__ loop and on macOS it
requires a running `CFRunLoop
<https://developer.apple.com/documentation/corefoundation/cfrunloop-rht>`__. You can use
rubicon-objc to integrate a Core Foundation CFRunLoop with asyncio:

.. code-block:: python

    import asyncio
    from rubicon.objc.eventloop import EventLoopPolicy

    # Install the event loop policy
    asyncio.set_event_loop_policy(EventLoopPolicy())

    # Get an event loop, and run it!
    loop = asyncio.get_event_loop()
    loop.run_forever()

Please refer to the `Rubicon Objective-C docs <https://rubicon-objc.readthedocs.io/en/latest/how-to/async.html>`__
for more information.

Notes on macOS
**************

On macOS 10.14 and higher, the implementation uses the ``UNUserNotificationCenter``
instead of the deprecated ``NSUserNotificationCenter``. ``UNUserNotificationCenter``
restricts sending desktop notifications to signed executables. This means that
notifications will only work the Python executable or bundled app has been signed. Note
that the installer from python.org provides a properly signed Python framework but
**homebrew does not**.

If you freeze your code with a PyInstaller or a similar package, you must sign the
resulting app bundle for notifications to work. An ad-hoc signature will be sufficient
but signing with an Apple developer certificate is recommended for distribution.
