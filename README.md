[![PyPi Release](https://img.shields.io/pypi/v/desktop-notifier.svg)](https://pypi.org/project/desktop-notifier/)
[![Pyversions](https://img.shields.io/pypi/pyversions/desktop-notifier.svg)](https://pypi.org/pypi/desktop-notifier/)
[![Documentation Status](https://readthedocs.org/projects/desktop-notifier/badge/?version=latest)](https://desktop-notifier.readthedocs.io/en/latest/?badge=latest)

# Desktop Notifier

`desktop-notifier`  is a Python library for cross-platform desktop notifications.
Currently supported platforms are:

* Linux via the dbus service org.freedesktop.Notifications
* macOS and iOS via the Notification Center framework

## Features

Where supported by the native platform APIs:

* Clickable notifications
* Notifications with buttons
* Notifications with reply fields
* Asyncio integration to execute callbacks on user interaction
* Notification sounds
* Limit maximum number of notifications shown in the notification center
* Pure Python dependencies only, no extension modules

## Installation

From PyPI:

```
pip3 install -U desktop-notifier
```

## Usage

Basic usage only requires the user to specify a notification title and message:

```Python
from desktop_notifier import DesktopNotifier

notifier = DesktopNotifier()
n = notifier.send(title="Hello world!", message="Notification body")

notifier.clear(n)  # removes the notification from the notification center
notifier.clear_all()  # removes all notifications for this app
```

By default, "Python" will be used as the app name for all notifications, but you can also
manually specify an app name and icon. Advanced usage also allows setting different
notification options such as urgency, buttons, callbacks, etc:

```Python
from desktop_notifier import DesktopNotifier, NotificationLevel

notifier = DesktopNotifier(
    app_name="Sample App",
    app_icon="file:///path/to/app_icon.png",
    notification_limit=10,
)

notifier.send(
    title="Julius Caesar",
    message="Et tu, Brute?",
    urgency=NotificationLevel.Critical,
    buttons={
        "Mark as read": lambda: print("Marked as read"),
    },
    reply_field=True,
    on_replied=lambda text: print("Brutus replied:", text),
    on_clicked=lambda: print("Notification clicked"),
    on_dismissed=lambda: print("Notification dismissed"),
    sound=True,
)
```

The above code will give the following result on macOS:

![gif](screenshots/macOS.gif)

Note that some platforms may not support all options. For instance, some Linux desktop
environments may not support notifications with buttons. macOS does not support
manually setting the app icon or name. Instead, both are always determined by the
application which uses the Library. This can be Python itself, when used interactively,
or a frozen app bundle when packaged with PyInstaller or similar solutions.

Any options or configurations which are not supported by the platform will be silently
ignored. Please refer to the documentation on [Read the Docs](https://desktop-notifier.readthedocs.io)
for more information on platform support.

Execution of callbacks requires a running event loop. On Linux, it requires a running
[asyncio](https://docs.python.org/3/library/asyncio.html) loop and on macOS it requires
a running
[CFRunLoop](https://developer.apple.com/documentation/corefoundation/cfrunloop-rht). You
can use [rubicon-objc](https://github.com/beeware/rubicon-objc) to integrate a Core
Foundation CFRunLoop with asyncio:

```Python
import asyncio
from rubicon.objc.eventloop import EventLoopPolicy

# Install the event loop policy
asyncio.set_event_loop_policy(EventLoopPolicy())

# Get an event loop, and run it!
loop = asyncio.get_event_loop()
loop.run_forever()
```

Please refer to the [Rubicon Objective-C docs](https://rubicon-objc.readthedocs.io/en/latest/how-to/async.html)
for more information.

## Notes on macOS

On macOS 10.14 and higher, the implementation uses the `UNUserNotificationCenter`
instead of the deprecated `NSUserNotificationCenter`. `UNUserNotificationCenter`
restricts sending desktop notifications to signed executables. This means that
notifications will only work the Python executable or bundled app has been signed. Note
that the installer from [python.org](https://python.org) provides a properly signed
Python framework but **homebrew does not** (manually signing the executable installed
by homebrew _should_ work as well).

If you freeze your code with PyInstaller or a similar package, you must sign the
resulting app bundle for notifications to work. An ad-hoc signature will be sufficient
but signing with an Apple developer certificate is recommended for distribution.

## Requirements

* macOS 10.13 or higher
* Linux desktop environment providing a dbus desktop notifications service

## Dependencies

* [dbus-next](https://github.com/altdesktop/python-dbus-next) on Linux
* [rubicon-objc](https://github.com/beeware/rubicon-objc) on macOS
