# v7.0.0

## Added:

* New `DispatchedNotification` class with the platform native notification identifier
  and runtime-updated status information about that notification
* New cross-platform implementation for `timeout`
* New `on_dispatched` event that is triggered when a notification was sent to the
  notifications server.
* New `on_cleared` event that is triggered when a notification is closed without
  user interaction (e.g. because it expired).
* Add class-level callbacks to `DesktopNotifierSync` as well

## Changed:

* `send` methods now return `DispatchedNotification` instances.
* `send` methods now also accept `DispatchedNotification` instances, allowing one to
  replace existing notifications with updated information; to do so simply create a
  new `DispatchedNotification` instance with the same `identifier`, but a different
  `Notification` instance
* `Notification` now accepts floats as `timeout`
* `Notification` and `Button` instances can now be initialized with `identifier=None`
* Interaction callbacks at the `DesktopNotifier` level now truly receive all events
  the notifications server signals; depending on the platform this might include
  interactions with notifications of other applications as well

## Fixed:

* Fixed sending notifications with a named sound resource on Linux
  (given that the notifications server has that capability)

# v6.0.0

## Added:

* You can now set interaction callbacks at the `DesktopNotifier` level which will be
  called on interactions with any notifications from the running app. Callbacks set on
  an individual notification take precedence if set. 

## Changed:

* `send` methods now return the notification ID instead of the notification instance.
* Notification objects are fully immutable.

## Fixed:

* Callbacks on notification dismissal not being called on macOS.

## Deprecated:

* Setting `notification_limit` will be ignored and logs a deprecation warning.

## Removed:

* Deprecated APIs from v5.0.0.

# v5.0.1

## Fixed:

* Fixed compatibility of type annotations with Python 3.8.

# v5.0.0

## Added:

* Support for custom notification sounds on all backends.
* Allow specifying sounds and icons either by name (for existing system sounds) or as a
  referenced by a URI or path.
* Allow specifying  attachments either by URI or path.
* Add a `get_capabilities()` API that returns which features are supported by a 
  platform.
* Compatibility with Ubuntu 20.04 and other older Dbus notification servers which do not
  conform to the current desktop notification API spec.
* A dedicated class `DesktopNotifierSync` with a blocking API instead of the async API 
  of `DesktopNotifier`.

## Changed:

* Removed code signing requirement for macOS binaries. Instead of preventing
  notification requests, only log a warning that notifications may fail. It is not
  documented which code signature checks an app must pass to send notifications and this
  allows apps that fail some of the checks and still send notifications.

## Fixed:

* Fixed a segfault on macOS when passing an attachment path that does not refer to an
  actual file.

## Deprecated:

* Deprecated specifying icons as strings. Use the `base.Icon` class instead.
* Deprecated specifying attachments as URI strings. Use the `base.Attachement` class
  instead.
* Deprecated specifying notification sounds as boolean (`True` = default sound,
  `False` = no sound). Use `base.DEFAULT_SOUND` for the system default and `None` for no
  sound instead. Use the `base.Sound` class for custom sounds.

## Removed:

* Removed the synchronous `DesktopNotifier.send_sync()` API. Use `DesktopNotifierSync`
  instead.

# v4.0.0

* Require winrt>=2.0, the first stable release of the Python to WinRT bridge.
* Fail gracefully when call for authorization fails on Windows with an OSError.
* Added type checking to Windows backend.
* Removed support for NSUserNotificationCenter. This means that macOS 10.13 and older
  are no longer supported.

# v3.5.6

* Remove importlib_resources dependency in favour of stdlib importlib.resources. This
  also fixes a breakage due to API changes in importlib_resources>=6.0.

# v3.5.4

* Fixes an issue with the `on_clicked` callback being shown as a button with label
  "default" on Xfce desktop environments.

# v3.5.3

* Adds a new API DesktopNotifier.send_notification(notification) which directly takes a
  notification instance as argument.
* Fixes an issue on macOS where type hints for ObjC classes where incorrectly
  interpreted due to the use of deferred type hint evaluation.

# v3.5.2

* Fixes missing default app icon.
* Fixes callbacks for interactions with grouped notifications on Windows.

# v3.5.0

* This release introduces proper Windows support after the windows backend has been in
  pre-release for some time.

# v3.4.3
 
* Handle gracefully if we cannot detect the App ID on Windows.

# v3.4.2

* Introduce support for notification timeouts, currently on Linux only.
* Improve error handling and detection in Windows implementation when asking for
  permission to send notifications and run background tasks.
* Update winsdk to v1.0.0b7 and make API adjustments.

# v3.4.1

Fixes an issue where passing `icon = ''` to `DesktopNotifier.send()` would always
default to using the app icon. This should only be the case when passing `icon = None`
which is the default value.

# v3.4.0

* Experimental support for Windows Toast notifications.

# v3.3.5

* Fixes callbacks not being called when pressing the button with index 0 when using the
  Dbus backend.

# v3.3.1

* Updated type hints and marked package as py.typed.

# v3.3.0

* Added support for notification urgencies in macOS 12 and iOS 15.
* Fixed a segfault when running from a non-framework build of Python on macOS 10.14 and
  higher.
