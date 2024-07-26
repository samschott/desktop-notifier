import platform
import asyncio

import pytest
import pytest_asyncio

from desktop_notifier import (
    Button,
    DesktopNotifier,
    DesktopNotifierSync,
    Notification,
    ReplyField,
)


if platform.system() == "Darwin":
    from rubicon.objc.eventloop import EventLoopPolicy

    asyncio.set_event_loop_policy(EventLoopPolicy())


@pytest_asyncio.fixture
async def notifier():
    dn = DesktopNotifier()
    # Skip requesting authorization to void blocking if not granted.
    dn._did_request_authorisation = True
    yield dn
    await dn.clear_all()


@pytest.fixture
def notifier_sync():
    dn = DesktopNotifierSync()
    # Skip requesting authorization to void blocking if not granted.
    dn._async_api._did_request_authorisation = True
    yield dn
    dn.clear_all()


@pytest.fixture
def notification():
    return Notification(
        title="Julius Caesar",
        message="Et tu, Brute?",
        buttons=[
            Button(
                title="Mark as read",
                on_pressed=lambda: print("Marked as read"),
            )
        ],
        reply_field=ReplyField(
            title="And Cassius, too?",
            button_title="Send it",
            on_replied=lambda text: print("Brutus replied:", text),
        ),
        on_clicked=lambda: print("Notification clicked"),
        on_dismissed=lambda: print("Notification dismissed"),
    )
