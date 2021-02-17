
Event loop integration
======================

Using the asynchronous API is highly recommended to prevent multiple milliseconds of
blocking IO from DBus or Cocoa APIs. In addition, execution of callbacks requires a
running event loop. On Linux, an asyncio event loop will be sufficient but macOS
requires a running `CFRunLoop <https://developer.apple.com/documentation/corefoundation/cfrunloop-rht)>`__.

You can use `rubicon-objc <https://github.com/beeware/rubicon-objc>`__ to integrate a
Core Foundation CFRunLoop with asyncio:

.. code-block:: python

    import asyncio
    from rubicon.objc.eventloop import EventLoopPolicy

    # Install the event loop policy
    asyncio.set_event_loop_policy(EventLoopPolicy())

    # Get an event loop, and run it!
    loop = asyncio.get_event_loop()
    loop.run_forever()


Desktop-notifier itself uses Rubicon Objective-C to interface with Cocoa APIs so you
will not be adding a new dependency. A full example integrating with the CFRunLoop is
given in examples folder. Please refer to the
`Rubicon Objective-C docs <https://rubicon-objc.readthedocs.io/en/latest/how-to/async.html>`__
for more information.

Likewise, you can integrate the asyncio event loop with a Gtk main loop on Gnome using
`gbulb <https://pypi.org/project/gbulbl>`__. This is not required for full functionality
but may be convenient when developing a Gtk app.
