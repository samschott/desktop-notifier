import platform
import asyncio

import pytest
from desktop_notifier import DesktopNotifier


if platform.system() == "Darwin":
    from rubicon.objc.eventloop import EventLoopPolicy

    asyncio.set_event_loop_policy(EventLoopPolicy())


@pytest.fixture
def notifier():
    return DesktopNotifier(app_name="Sample App")
