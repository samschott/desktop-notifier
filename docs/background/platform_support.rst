
Platform support
================

Some platforms may not support all options. For instance, some Linux desktop
environments may not support notifications with buttons. macOS does not support
manually setting the app icon or name. Instead, both are always determined by the
application which uses the Library. This can be Python itself, when used interactively,
or a frozen app bundle when packaged with PyInstaller or similar solutions.

The table below gives an overview over supported functionality for different platforms.

.. csv-table::
   :header: "Option", "Description", "Linux", "macOS"
   :widths: 5, 5, 5, 5

   "app_name", "The application name to display", "✓", "-- [#f1]_"
   "app_icon", "The icon shown with the notification", "✓", "-- [#f1]_"
   "title", "The notification title", "✓", "✓"
   "message", "The notification message", "✓", "✓"
   "urgency", "Urgency level that determines how the notification is displayed", "✓", "--"
   "action", "A callback when the notification is clicked", "✓ [#f2]_", "✓"
   "buttons", "Support for one or more buttons with callbacks", "✓ [#f2]_", "✓ [#f3]_"
   "sound", "Play a default sound when showing the notification", "✓ [#f2]_", "✓"

.. [#f1] App name and icon on macOS are automatically determined by the calling application.
.. [#f2] May be ignored by some notification servers, depending on the desktop environment.
.. [#f3] Only a single button is supported by our implementation for macOS 10.13 and lower.
