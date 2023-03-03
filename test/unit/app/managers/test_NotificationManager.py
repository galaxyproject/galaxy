import json

from galaxy.managers.notification import NotificationManager
from galaxy.schema.notifications import (
    MessageNotificationContent,
    NotificationCreateData,
    NotificationCreateRequest,
    NotificationRecipients,
)
from .base import BaseTestCase

# =============================================================================
default_password = "123456"
user2_data = dict(email="user2@user2.user2", username="user2", password=default_password)
# =============================================================================


class TestNotificationManager(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.notification_manager = NotificationManager(self.trans.sa_session)

    def test_create_notification_for_users(self):
        user = self.user_manager.create(**user2_data)
        request = NotificationCreateRequest(
            recipients=NotificationRecipients.construct(
                user_ids=[user.id],
            ),
            notification=NotificationCreateData(
                source="testing",
                variant="info",
                category="message",
                content=MessageNotificationContent(subject="Testing Subject", message="Testing Message"),
                publication_time=None,
                expiration_time=None,
            ),
        )
        notification, notifications_sent = self.notification_manager.create_notification_for_users(request)
        assert notifications_sent == 1
        assert notification.id
        assert notification.category == "message"
        notification_content = json.loads(notification.content)
        assert notification_content["category"] == "message"
        assert notification_content["subject"] == "Testing Subject"
        assert notification_content["message"] == "Testing Message"

    # TODO: Fix everything and test _get_all_recipient_users
