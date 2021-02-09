
Platform support
================

Some platforms may not support all options. For instance, some Linux desktop
environments may not support notifications with buttons. macOS does not support
manually setting the app icon or name. Instead, both are always determined by the
application which uses the Library. This can be Python itself, when used interactively,
or a frozen app bundle when packaged with PyInstaller or similar solutions.

The table below gives an overview over supported functionality for different platforms.

.. csv-table::
   :header: "Option", "Description", "Linux", "macOS/iOS"
   :widths: 5, 5, 5, 5

   "app_name", "The application name to display", "✓", "-- [#f1]_"
   "app_icon", "The icon shown with the notification", "✓", "-- [#f1]_"
   "title", "The notification title", "✓", "✓"
   "message", "The notification message", "✓", "✓"
   "urgency", "Urgency level that determines how the notification is displayed", "✓", "--"
   "buttons", "Support for one or more buttons with callbacks", "✓ [#f2]_", "✓ [#f3]_"
   "reply_field", "Whether to show a reply field", "--", "✓"
   "on_clicked", "A callback to invoke when the notification is clicked", "✓ [#f2]_", "✓"
   "on_dismissed", "A callback to invoke when the notification is dismissed", "✓ [#f2]_", "✓"
   "on_replied", "A callback to invoke when the user replies", "--", "✓"
   "sound", "Play a default sound when showing the notification", "✓ [#f2]_", "✓"
   "thread", "An identifier to group notifications together", "--", "✓"

.. [#f1] App name and icon on macOS are automatically determined by the calling application.
.. [#f2] May be ignored by some notification servers, depending on the desktop environment.
.. [#f3] Only a single button is supported by our implementation for macOS 10.13 and lower.


Callbacks
*********

MacOS and almost all Linux notification servers support executing a callback when the
notification is clicked. Note the requirements on a running event loop to handle
callbacks in Python.

Buttons
*******

Our implementation for macOS 10.13 and lower supports only a single button. On iOS and
macOS 10.14+, we support an unlimited number of buttons.

Linux desktop environments and notification servers may or may not support a varying
number of buttons. Gnome desktops typically support up to three buttons.

When an implementation or a platform supports only a limited number of buttons, any
additional buttons specified in the notification request will be silently ignored.

Reply field
***********

Reply fields are supported on macOS and iOS. If ``reply_field`` is set to True, a
"Reply" button and text input field will be show. The button will always placed first,
before any other buttons. The placeholder and button text are currently not
customisable, even when allowed by the native platform APIs.

Attachments
***********

MacOS 10.14+ and iOS support attaching a local file to the notification and may show a
preview of the file. Allowed file types are:

* An audio file up to 5 MB: AIFF, WAV, MP3, or MPEG4
* An image file up to 10 MB: JPEG, GIF, or PNG
* A video file up to 50 MB: MPEG, MPEG2, MPEG4, or AVI

On macOS, only previews of image attachments will be shown. iOS will show previews of
all of the above attachment types and allows long-pressing the notification to show the
full attachment.

Linux notification servers may support attaching a secondary image to the notification,
shown in addition to the app icon. Where this is not supported, the app icon will be
replaced by a thumbnail of the image. This currently the case for Gnome.
