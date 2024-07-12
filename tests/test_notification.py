CATEGORY_ID = "desktop-notifier__button-title-Mark as read" \
              "__reply-title-And Cassius, too?__reply-button-title-Send it"


def test_category_id(notification):
    assert notification.category_id() == CATEGORY_ID
