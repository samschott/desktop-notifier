# v5.0.0

* Add support for custom sounds on all backends.
* Expand API to allow passing sounds and icons that are specified either by name (for
  existing system sounds) or by URI or path for custom resources.
* Expand attachment API to allow passing a URI or path.
* Fixes segfaults on macOS when passing an attachment path that does not refer to an
  actual file.
* Add a `capabilities()` API that returns which features are supported by a platform.

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

* Fixes callbacks not being called when pressing the button with index 0 when using the Dbus backend.

# v3.3.1

* Updated type hints and marked package as py.typed.

# v3.3.0

* Added support for notification urgencies in macOS 12 and iOS 15.
* Fixed a segfault when running from a non-framework build of Python on macOS 10.14 and higher.