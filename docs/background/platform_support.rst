
Platform support
================

Some platforms may not support all options. For instance, some Linux desktop
environments don't support notifications with buttons. macOS and Windows don't support
manually setting the app icon or name but determine those automatically from the
application which uses the Library.

The table below gives an overview over supported functionality for different platforms.
Please refer to the platform documentation for more detailed information:

* macOS / iOS: `UNUserNotificationCenter`_
* Linux: `org.freedesktop.Notifications`_
* Windows: `Toast Notifications`_

.. csv-table::
   :header: "Option", "Description", "Linux", "macOS/iOS", "Windows"

   "app_name", "The application name to display", "✓", "-- [#f1]_", "-- [#f1]_"
   "app_icon", "The icon shown with the notification", "✓", "-- [#f1]_", "-- [#f1]_"
   "title", "The notification title", "✓", "✓", "✓"
   "message", "The notification message", "✓", "✓", "✓"
   "urgency", "Determines persistence and appearance", "✓ [#f2]_", "✓ [#f3]_", "✓"
   "buttons", "One or more buttons with callbacks", "✓ [#f4]_", "✓", "✓ [#f4]_"
   "reply_field", "An interactive reply field", "--", "✓", "✓"
   "on_clicked", "A callback to invoke on click", "✓", "✓", "✓"
   "on_dismissed", "A callback to invoke on dismissal", "✓", "✓", "✓"
   "sound", "Play a sound with the notification", "✓ [#f2]_", "✓ [#f5]_", "✓"
   "thread", "An identifier to group notifications together", "--", "✓", "✓"
   "attachment", "File attachment, e.g., an image", "✓ [#f2]_ [#f6]_", "✓ [#f6]_", "✓ [#f6]_"
   "timeout", "Duration in seconds until notification auto-dismissal", "✓", "✓", "✓"

.. [#f1] App name and icon on macOS and Windows are automatically determined by the
         calling application.
.. [#f2] May be ignored by some Linux notification servers.
.. [#f3] Only on macOS 12 and later.
.. [#f4] Number of buttons may be limited. See section below.
.. [#f5] macOS only supports named sounds, e.g., from `/System/Library/Sounds`.
.. [#f6] Limitations on file types exist for each platform. See section below.

Callbacks
*********

MacOS, Windows and almost all Linux notification servers support executing a callback
when the notification is clicked. Note the requirements on a running event loop to
handle callbacks in Python.

Urgency
*******

The notification urgency may influence how a notification is displayed. For instance, in
Gnome, notifications of critical urgency will remain visible until closed by the user
and their buttons will always be expanded.

On macOS, critical notifications require a special app entitlement issued by Apple.

Buttons
*******

macOS supports an unlimited number of buttons.

Linux desktop environments and notification servers may or may not support a varying
number of buttons. Gnome desktops typically support up to three buttons.

Windows supports up to 5 buttons.

When an implementation or a platform supports only a limited number of buttons, any
additional buttons specified in the notification request will be silently ignored.

Attachments
***********

MacOS 10.14+ and iOS support attaching a local file to the notification and may show a
preview of the file. Allowed file types are:

* An audio file up to 5 MB: AIFF, WAV, MP3, or MPEG4
* An image file up to 10 MB: JPEG, GIF, or PNG
* A video file up to 50 MB: MPEG, MPEG2, MPEG4, or AVI

On macOS, only previews of image attachments will be shown. iOS will show previews of
all of the above attachment types and allows long-pressing the notification to show the
full attachment. The notification will still be shown if the attachment cannot be loaded.

Windows supports images only. The image URI must be a web url or point to a resource
bundled with the app.

Linux notification servers may support attaching a secondary image to the notification,
shown in addition to the app icon. Where this is not supported, the app icon will be
replaced by a thumbnail of the image. This is currently the case for Gnome.

.. _UNUserNotificationCenter: https://developer.apple.com/documentation/usernotifications/unusernotificationcenter
.. _org.freedesktop.Notifications: https://specifications.freedesktop.org/notification-spec/notification-spec-latest.html
.. _Toast Notifications: https://docs.microsoft.com/windows/apps/design/shell/tiles-and-notifications/adaptive-interactive-toasts
