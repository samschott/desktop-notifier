[![PyPi Release](https://img.shields.io/pypi/v/desktop-notifier.svg)](https://pypi.org/project/desktop-notifier/)
[![Pyversions](https://img.shields.io/pypi/pyversions/desktop-notifier.svg)](https://pypi.org/pypi/desktop-notifier/)
[![Documentation Status](https://readthedocs.org/projects/desktop-notifier/badge/?version=latest)](https://desktop-notifier.readthedocs.io/en/latest/?badge=latest)

# Desktop Notifier

`desktop-notifier`  is a Python library for cross-platform desktop notifications.
Currently supported platforms are:

* Linux via the dbus service org.freedesktop.Notifications
* macOS via the Notification Center framework

## Features

* Clickable notifications (requires platform support)
* Notifications with buttons (requires platform support)
* Asyncio integration to execute callbacks on user interaction
* Limit maximum number of notification shown in the notification history
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
notifier.send(title="Hello world!", message="Notification body")
```

By default, "Python" will be used as the app name for all notification. Advanced usage
allows specifying the app name, notification urgency, app icon, buttons and callbacks:

```Python
from desktop_notifier import DesktopNotifier, NotificationLevel

notifier = DesktopNotifier(app_name="Sample App", notification_limit=10)
notifier.send(
    title="Hello from Python!",
    message="A horrible exception occured",
    urgency=NotificationLevel.Critical,
    icon="/path/to/icon.png",
    action=lambda: print("notification clicked"),
    buttons={
        "Button 1": lambda: print("Button 1 clicked"),
        "Button 2": lambda: print("Button 2 clicked"),
    },
)
```

Note that some platforms may not support all options. For instance, some Linux desktop
environments may not support notifications with buttons. macOS does not support
manually setting the app icon or name. Instead, both are always determined by the
application which uses the Library. This can be Python itself, when used interactively,
or a frozen app bundle when packaged with PyInstaller or similar solutions. Any options
or configurations which are not supported by the platform will be silently ignored.

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
restricts sending desktop notifications to signed frameworks or app bundles. This means
that notifications will only work if Python has been installed as a Framework and
properly signed. This is the case when using the installer from python.org but **not for
homebrew installations**.

If you are planning to use this library in an app bundle, you must sign the app bundle
to send notifications, either with an Apple Developer certificate or ad-hoc for local
usage.

## Requirements

* macOS 10.13 or higher
* Linux desktop environment providing a dbus desktop notifications service

## Dependencies

* [dbus-next](https://github.com/altdesktop/python-dbus-next) on Linux
* [rubicon-objc](https://github.com/beeware/rubicon-objc) on macOS
