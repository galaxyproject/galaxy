import json
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import pytest

from galaxy.exceptions import ObjectNotFound
from galaxy.managers.notification import NotificationManager
from galaxy.model import User
from galaxy.schema.notifications import (
    ActionLink,
    BroadcastNotificationContent,
    BroadcastNotificationCreateRequest,
    MessageNotificationContent,
    NotificationCategorySettings,
    NotificationChannelSettings,
    NotificationCreateData,
    NotificationCreateRequest,
    NotificationRecipients,
    PersonalNotificationCategory,
    UpdateUserNotificationPreferencesRequest,
    UserNotificationPreferences,
    UserNotificationUpdateRequest,
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
        notification, notifications_sent = self._send_notification_to_users([user])

        assert notifications_sent == 1
        assert notification.id
        assert notification.category == "message"
        notification_content = json.loads(notification.content)
        assert notification_content["category"] == "message"
        assert notification_content["subject"] == "Testing Subject"
        assert notification_content["message"] == "Testing Message"

    def test_create_notification_broadcast(self):
        request = BroadcastNotificationCreateRequest(
            variant="warning",
            source="testing",
            content=BroadcastNotificationContent(
                subject="Testing Broadcast Subject",
                message="Testing Broadcast Message",
                action_links=[
                    ActionLink(
                        action_name="Go to Poll",
                        link="https://link_to_anonymous.test/poll",
                    ),
                ],
            ),
        )
        notification = self.notification_manager.create_broadcast_notification(request)

        assert notification.id
        assert notification.category == "broadcast"
        notification_content = json.loads(notification.content)
        assert notification_content["category"] == "broadcast"
        assert notification_content["subject"] == "Testing Broadcast Subject"
        assert notification_content["message"] == "Testing Broadcast Message"
        action_links = notification_content["action_links"]
        assert len(action_links) == 1
        assert action_links[0]["action_name"] == "Go to Poll"
        assert action_links[0]["link"] == "https://link_to_anonymous.test/poll"

    def test_get_user_notifications(self):
        user = self.user_manager.create(**user2_data)
        user_notifications = self.notification_manager.get_user_notifications(user)
        assert len(user_notifications) == 0

        self._send_notification_to_users([user])

        user_notifications = self.notification_manager.get_user_notifications(user)
        assert len(user_notifications) == 1

    def test_get_user_notification(self):
        user = self.user_manager.create(**user2_data)
        notification, _ = self._send_notification_to_users([user])

        user_notification = self.notification_manager.get_user_notification(user, notification.id)

        assert user_notification
        assert user_notification.id
        assert user_notification.source == "testing"
        assert user_notification.variant == "info"
        assert user_notification.category == "message"
        assert user_notification.publication_time is not None
        assert user_notification.expiration_time is not None
        assert user_notification.content
        user_notification_content = json.loads(user_notification.content)
        assert user_notification_content["category"] == "message"
        assert user_notification_content["subject"] == "Testing Subject"
        assert user_notification_content["message"] == "Testing Message"
        assert user_notification.seen_time is None
        assert user_notification.favorite is False
        assert user_notification.deleted is False

    def test_update_user_notifications(self):
        user = self.user_manager.create(**user2_data)
        notification, _ = self._send_notification_to_users([user])
        user_notification = self.notification_manager.get_user_notification(user, notification.id)
        assert user_notification.seen_time is None
        assert user_notification.favorite is False
        assert user_notification.deleted is False
        request = UserNotificationUpdateRequest(seen=True, favorite=True)
        self.notification_manager.update_user_notifications(user, set([notification.id]), request)
        user_notification = self.notification_manager.get_user_notification(user, notification.id)
        assert user_notification.seen_time is not None
        assert user_notification.favorite is True

    def test_get_user_notification_preferences_returns_default_preferences(self):
        user = self.user_manager.create(**user2_data)
        default_preferences = UserNotificationPreferences.default()

        preferences = self.notification_manager.get_user_notification_preferences(user)

        assert preferences == default_preferences

    def test_update_user_notification_preferences(self):
        user = self.user_manager.create(**user2_data)
        preferences = self.notification_manager.get_user_notification_preferences(user)
        message_preferences = preferences.__root__.get(PersonalNotificationCategory.message)
        assert message_preferences
        assert message_preferences.enabled is True
        assert message_preferences.channels.push is True

        update_request = UpdateUserNotificationPreferencesRequest(
            preferences=UserNotificationPreferences(
                __root__={
                    PersonalNotificationCategory.message: NotificationCategorySettings(
                        enabled=False,
                        channels=NotificationChannelSettings(push=False),
                    ),
                }
            )
        )
        updated_preferences = self.notification_manager.update_user_notification_preferences(user, update_request)

        updated_preferences = self.notification_manager.get_user_notification_preferences(user)
        message_preferences = updated_preferences.__root__.get(PersonalNotificationCategory.message)
        assert message_preferences
        assert message_preferences.enabled is False
        assert message_preferences.channels.push is False

    def test_cleanup_expired_notifications(self):
        user = self.user_manager.create(**user2_data)
        now = datetime.utcnow()
        notification, _ = self._send_notification_to_users([user], notification={"expiration_time": now})
        user_notification = self.notification_manager.get_user_notification(user, notification.id, active_only=False)
        assert user_notification
        assert self._has_expired(user_notification.expiration_time) is True

        self.notification_manager.cleanup_expired_notifications()

        with pytest.raises(ObjectNotFound):
            self.notification_manager.get_user_notification(user, notification.id, active_only=False)

    def _send_notification_to_users(self, users: List[User], notification: Optional[Dict[str, Any]] = None):
        notification_data = NotificationCreateData(
            source="testing",
            variant="info",
            category="message",
            content=MessageNotificationContent(subject="Testing Subject", message="Testing Message"),
            publication_time=None,
            expiration_time=None,
        )
        notification_data = notification_data.copy(update=notification)
        request = NotificationCreateRequest(
            recipients=NotificationRecipients.construct(
                user_ids=[user.id for user in users],
            ),
            notification=notification_data,
        )
        notification, notifications_sent = self.notification_manager.create_notification_for_users(request)
        return notification, notifications_sent

    def _has_expired(self, expiration_time: Optional[datetime]) -> bool:
        return expiration_time < datetime.utcnow() if expiration_time else False
