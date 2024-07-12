import pytest

from desktop_notifier.macos import CocoaNotificationCenter


@pytest.fixture(scope='session')
def notification_center() -> CocoaNotificationCenter:
    return CocoaNotificationCenter()


def test_category_id(notification, notification_center):
    assert notification_center._category_id(notification) == 'desktop-notifier__button-title-Mark as read__reply-title-Reply__reply-button-title-Send'
