import platform
import asyncio

import pytest
from desktop_notifier import DesktopNotifier


if platform.system() == "Darwin":
    from rubicon.objc.eventloop import EventLoopPolicy

    asyncio.set_event_loop_policy(EventLoopPolicy())


@pytest.fixture
def notifier():
    dn = DesktopNotifier()
    # Skip requesting authorization to void blocking if not granted.
    dn._did_request_authorisation = True
    return dn
