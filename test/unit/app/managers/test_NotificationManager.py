from galaxy.managers.notification import NotificationManager
from .base import BaseTestCase

# =============================================================================
default_password = "123456"
user2_data = dict(email="user2@user2.user2", username="user2", password=default_password)
# =============================================================================


class TestNotificationManager(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.notification_manager = NotificationManager(self.trans.sa_session)

    def test_create_notification(self):
        notification = self.notification_manager.create(content="New notification")
        assert notification.id
        assert notification.content == "New notification"

    def test_update_notification(self):
        notification = self.notification_manager.create(content="New notification")
        updated_content = "Updated notification"
        self.notification_manager.update(notification.id, updated_content)
        assert notification.content == updated_content

    def test_associate_user_notification(self):
        user = self.user_manager.create(**user2_data)
        notification = self.notification_manager.create(content="New notification")
        self.notification_manager.associate_user_notification([user.id], notification)
        assert len(user.all_notifications) == 1
        assert len(notification.user_notification_associations) == 1
        for association in notification.user_notification_associations:
            assert association.user_id == user.id
            assert association.notification_id == notification.id
