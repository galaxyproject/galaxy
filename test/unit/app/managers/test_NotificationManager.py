from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
)
from unittest.mock import patch

import pytest

from galaxy.exceptions import ObjectNotFound
from galaxy.managers.notification import (
    DefaultStrategy,
    NotificationManager,
    NotificationRecipientResolver,
)
from galaxy.model import (
    Group,
    Role,
    User,
)
from galaxy.schema.notifications import (
    BroadcastNotificationContent,
    BroadcastNotificationCreateRequest,
    NotificationBroadcastUpdateRequest,
    NotificationCategorySettings,
    NotificationChannelSettings,
    NotificationCreateData,
    NotificationCreateRequest,
    NotificationRecipients,
    NotificationVariant,
    PersonalNotificationCategory,
    UpdateUserNotificationPreferencesRequest,
    UserNotificationPreferences,
    UserNotificationUpdateRequest,
)
from .base import BaseTestCase


class NotificationsBaseTestCase(BaseTestCase):
    def _create_test_user(self, username="user1") -> User:
        user_data = dict(email=f"{username}@user.email", username=username, password="password")
        user = self.user_manager.create(**user_data)
        return user

    def _create_test_users(self, num_users: int = 1) -> List[User]:
        users = [self._create_test_user(f"username{num:02}") for num in range(num_users)]
        return users


class NotificationManagerBaseTestCase(NotificationsBaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.notification_manager = NotificationManager(self.trans.sa_session, self.app.config)

    def _default_test_notification_data(self):
        """Dictionary with default values for a simple Message notification."""
        return {
            "source": "testing",
            "variant": "info",
            "category": "message",
            "content": {
                "category": "message",
                "subject": "Testing Subject",
                "message": "Testing Message",
            },
        }

    def _send_message_notification_to_users(self, users: List[User], notification: Optional[Dict[str, Any]] = None):
        data = self._default_test_notification_data()
        if notification:
            data.update(notification)
        notification_data = NotificationCreateData(**data)

        request = NotificationCreateRequest(
            recipients=NotificationRecipients.model_construct(
                user_ids=[user.id for user in users],
            ),
            notification=notification_data,
            galaxy_url="https://test.galaxy.url",
        )
        created_notification, notifications_sent = self.notification_manager.send_notification_to_recipients(request)
        return created_notification, notifications_sent

    def _has_expired(self, expiration_time: Optional[datetime]) -> bool:
        return expiration_time < datetime.utcnow() if expiration_time else False

    def _assert_notification_expected(self, actual_notification: Any, expected_notification: Dict[str, Any]):
        assert actual_notification
        assert actual_notification.id
        assert actual_notification.source == expected_notification["source"]
        assert actual_notification.variant == expected_notification["variant"]
        assert actual_notification.category == expected_notification["category"]

        if expected_publication_time := expected_notification.get("publication_time"):
            assert actual_notification.publication_time == expected_publication_time
        else:
            assert actual_notification.publication_time is not None

        if expected_expiration_time := expected_notification.get("expiration_time"):
            assert actual_notification.expiration_time == expected_expiration_time
        else:
            assert actual_notification.expiration_time is not None

        assert actual_notification.content
        user_notification_content = actual_notification.content
        assert user_notification_content["category"] == expected_notification["content"]["category"]
        assert user_notification_content["subject"] == expected_notification["content"]["subject"]
        assert user_notification_content["message"] == expected_notification["content"]["message"]


class NotificationManagerBaseTestCaseWithTasks(NotificationManagerBaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.app.config.enable_celery_tasks = True
        self.notification_manager = NotificationManager(self.trans.sa_session, self.app.config)


class TestBroadcastNotifications(NotificationManagerBaseTestCase):
    def test_create_notification_broadcast(self):
        data = self._default_broadcast_notification_data()
        actual_notification = self._send_broadcast_notification(data)

        assert actual_notification.id
        assert actual_notification.category == "broadcast"
        notification_content = actual_notification.content
        assert notification_content["category"] == "broadcast"
        assert notification_content["subject"] == "Testing Broadcast Subject"
        assert notification_content["message"] == "Testing Broadcast Message"
        action_links = notification_content["action_links"]
        assert len(action_links) == 1
        assert action_links[0]["action_name"] == "Go to Survey"
        assert action_links[0]["link"] == "https://link_to_anonymous.test/survey"

    def test_get_broadcasted_notification(self):
        notification_data = self._default_broadcast_notification_data()
        created_notification = self._send_broadcast_notification(notification_data)

        actual_notification = self.notification_manager.get_broadcasted_notification(created_notification.id)

        assert actual_notification.id == created_notification.id

    def test_get_all_broadcasted_notifications(self):
        now = datetime.utcnow()
        next_week = now + timedelta(days=7)
        next_month = now + timedelta(days=30)

        notification_data = self._default_broadcast_notification_data()
        notification_data["content"]["subject"] = "Recent Notification"
        notification_data["publication_time"] = now
        self._send_broadcast_notification(notification_data)

        notification_data = self._default_broadcast_notification_data()
        notification_data["content"]["subject"] = "Scheduled Next Week Notification"
        notification_data["publication_time"] = next_week
        self._send_broadcast_notification(notification_data)

        notification_data = self._default_broadcast_notification_data()
        notification_data["content"]["subject"] = "Scheduled Next Month Notification"
        notification_data["publication_time"] = next_month
        self._send_broadcast_notification(notification_data)

        notifications = self.notification_manager.get_all_broadcasted_notifications()
        assert len(notifications) == 1
        assert notifications[0].content["subject"] == "Recent Notification"

        notifications = self.notification_manager.get_all_broadcasted_notifications(since=next_week, active_only=False)
        assert len(notifications) == 2
        assert notifications[0].content["subject"] == "Scheduled Next Week Notification"
        assert notifications[1].content["subject"] == "Scheduled Next Month Notification"

        notifications = self.notification_manager.get_all_broadcasted_notifications(since=next_month, active_only=False)
        assert len(notifications) == 1
        assert notifications[0].content["subject"] == "Scheduled Next Month Notification"

    def test_update_broadcasted_notification(self):
        next_month = datetime.utcnow() + timedelta(days=30)
        notification_data = self._default_broadcast_notification_data()
        notification_data["content"]["subject"] = "Old Scheduled Notification"
        notification_data["publication_time"] = next_month
        actual_notification = self._send_broadcast_notification(notification_data)

        now = datetime.utcnow()
        expected_content = BroadcastNotificationContent(subject="Updated Notification", message="Updated Message")
        update_request = NotificationBroadcastUpdateRequest(
            source="updated_source",
            variant=NotificationVariant.warning,
            publication_time=now,
            content=expected_content,
        )
        updated_count = self.notification_manager.update_broadcasted_notification(
            actual_notification.id, update_request
        )
        assert updated_count == 1
        updated_notification = self.notification_manager.get_broadcasted_notification(actual_notification.id)
        assert updated_notification.source == update_request.source
        assert updated_notification.variant == update_request.variant
        assert updated_notification.publication_time == update_request.publication_time
        content = updated_notification.content
        assert content["subject"] == expected_content.subject
        assert content["message"] == expected_content.message

    def test_cleanup_expired_broadcast_notifications(self):
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        notification_data = self._default_broadcast_notification_data()
        notification_data["expiration_time"] = one_hour_ago
        actual_notification = self._send_broadcast_notification(notification_data)
        assert self._has_expired(actual_notification.expiration_time) is True

        result = self.notification_manager.cleanup_expired_notifications()
        assert result.deleted_notifications_count == 1
        assert result.deleted_associations_count == 0

        with pytest.raises(ObjectNotFound):
            self.notification_manager.get_broadcasted_notification(actual_notification.id, active_only=False)

    def _default_broadcast_notification_data(self):
        return {
            "source": "testing",
            "variant": "warning",
            "content": {
                "category": "broadcast",
                "subject": "Testing Broadcast Subject",
                "message": "Testing Broadcast Message",
                "action_links": [
                    {
                        "action_name": "Go to Survey",
                        "link": "https://link_to_anonymous.test/survey",
                    },
                ],
            },
        }

    def _send_broadcast_notification(self, broadcast_notification_data: Dict[str, Any]):
        request = BroadcastNotificationCreateRequest(**broadcast_notification_data)
        created_notification = self.notification_manager.create_broadcast_notification(request)
        return created_notification


class TestUserNotifications(NotificationManagerBaseTestCase):
    def test_create_notification_for_users(self):
        num_target_users = 2
        users = self._create_test_users(num_users=num_target_users)
        expected_notification = self._default_test_notification_data()
        expected_notification["source"] = "test_create_notification_for_users"
        actual_notification, actual_notifications_sent = self._send_message_notification_to_users(
            users, notification=expected_notification
        )

        assert actual_notifications_sent == num_target_users
        self._assert_notification_expected(actual_notification, expected_notification)

    def test_get_user_notifications(self):
        user = self._create_test_user()
        user_notifications = self.notification_manager.get_user_notifications(user)
        assert len(user_notifications) == 0

        self._send_message_notification_to_users([user])

        user_notifications = self.notification_manager.get_user_notifications(user)
        assert len(user_notifications) == 1

    def test_get_user_notification(self):
        user = self._create_test_user()
        expected_user_notification = self._default_test_notification_data()
        notification, _ = self._send_message_notification_to_users([user], notification=expected_user_notification)

        actual_user_notification = self.notification_manager.get_user_notification(user, notification.id)

        self._assert_notification_expected(actual_user_notification, expected_user_notification)
        assert actual_user_notification._mapping["seen_time"] is None
        assert actual_user_notification._mapping["deleted"] is False

    def test_update_user_notifications(self):
        user = self._create_test_user()
        notification, _ = self._send_message_notification_to_users([user])
        user_notification = self.notification_manager.get_user_notification(user, notification.id)
        assert user_notification.seen_time is None
        assert user_notification.deleted is False
        request = UserNotificationUpdateRequest(seen=True)
        self.notification_manager.update_user_notifications(user, {notification.id}, request)
        user_notification = self.notification_manager.get_user_notification(user, notification.id)
        assert user_notification.seen_time is not None
        assert user_notification.deleted is False

    def test_scheduled_notifications(self):
        user = self._create_test_user()
        tomorrow = datetime.utcnow() + timedelta(hours=24)
        expected_notification = self._default_test_notification_data()
        expected_notification["source"] = "test_scheduled"
        expected_notification["publication_time"] = tomorrow
        actual_notification, actual_notifications_sent = self._send_message_notification_to_users(
            [user], notification=expected_notification
        )
        assert actual_notifications_sent == 1
        self._assert_notification_expected(actual_notification, expected_notification)

        # The user cannot access the notification
        user_notifications = self.notification_manager.get_user_notifications(user)
        assert len(user_notifications) == 0
        with pytest.raises(ObjectNotFound):
            self.notification_manager.get_user_notification(user, actual_notification.id)

        # Because is not active yet
        active_only = False
        user_notification = self.notification_manager.get_user_notification(
            user, actual_notification.id, active_only=active_only
        )
        self._assert_notification_expected(user_notification, expected_notification)

    def test_get_user_notification_preferences_returns_default_preferences(self):
        user = self._create_test_user()
        default_preferences = UserNotificationPreferences.default()

        actual_preferences = self.notification_manager.get_user_notification_preferences(user)

        assert actual_preferences == default_preferences

    def test_update_user_notification_preferences(self):
        user = self._create_test_user()
        preferences = self.notification_manager.get_user_notification_preferences(user)
        message_preferences = preferences.get(PersonalNotificationCategory.message)
        assert message_preferences
        assert message_preferences.enabled is True
        assert message_preferences.channels.push is True

        update_request = UpdateUserNotificationPreferencesRequest(
            preferences={
                PersonalNotificationCategory.message: NotificationCategorySettings(
                    enabled=False,
                    channels=NotificationChannelSettings(push=False),
                ),
            }
        )
        updated_preferences = self.notification_manager.update_user_notification_preferences(user, update_request)

        updated_preferences = self.notification_manager.get_user_notification_preferences(user)
        message_preferences = updated_preferences.get(PersonalNotificationCategory.message)
        assert message_preferences
        assert message_preferences.enabled is False
        assert message_preferences.channels.push is False

    def test_cleanup_expired_notifications(self):
        user = self._create_test_user()
        now = datetime.utcnow()
        notification, _ = self._send_message_notification_to_users([user], notification={"expiration_time": now})
        user_notification = self.notification_manager.get_user_notification(user, notification.id, active_only=False)
        assert user_notification
        assert self._has_expired(user_notification.expiration_time) is True

        result = self.notification_manager.cleanup_expired_notifications()
        assert result.deleted_notifications_count == 1
        assert result.deleted_associations_count == 1

        with pytest.raises(ObjectNotFound):
            self.notification_manager.get_user_notification(user, notification.id, active_only=False)

    def test_users_do_not_receive_opt_out_notifications(self):
        users = self._create_test_users(num_users=2)
        user_opt_out = users[0]
        user_opt_in = users[1]
        update_request = UpdateUserNotificationPreferencesRequest(
            preferences={
                PersonalNotificationCategory.message: NotificationCategorySettings(enabled=False),
            }
        )
        self.notification_manager.update_user_notification_preferences(user_opt_out, update_request)
        self._send_message_notification_to_users(users)

        user_notifications = self.notification_manager.get_user_notifications(user_opt_out)
        assert len(user_notifications) == 0
        user_notifications = self.notification_manager.get_user_notifications(user_opt_in)
        assert len(user_notifications) == 1

    def test_urgent_notifications_ignore_preferences(self):
        user = self._create_test_user()
        update_request = UpdateUserNotificationPreferencesRequest(
            preferences={
                PersonalNotificationCategory.message: NotificationCategorySettings(enabled=False),
            }
        )
        self.notification_manager.update_user_notification_preferences(user, update_request)

        # Send normal message notification
        notification_data = self._default_test_notification_data()
        self._send_message_notification_to_users([user], notification=notification_data)
        user_notifications = self.notification_manager.get_user_notifications(user)
        assert len(user_notifications) == 0

        # Send urgent message notification
        notification_data["variant"] = NotificationVariant.urgent
        self._send_message_notification_to_users([user], notification=notification_data)
        user_notifications = self.notification_manager.get_user_notifications(user)
        assert len(user_notifications) == 1


class TestUserNotificationsWithTasks(NotificationManagerBaseTestCaseWithTasks):

    def test_urgent_notifications_via_email_channel(self):
        user = self._create_test_user()
        # Disable email channel only
        update_request = UpdateUserNotificationPreferencesRequest(
            preferences={
                PersonalNotificationCategory.message: NotificationCategorySettings(
                    enabled=True,
                    channels=NotificationChannelSettings(email=False),
                ),
            }
        )
        self.notification_manager.update_user_notification_preferences(user, update_request)

        emails_sent = []

        def validate_send_email(frm, to, subject, body, config, html=None):
            emails_sent.append(
                {
                    "frm": frm,
                    "to": to,
                    "subject": subject,
                    "body": body,
                    "config": config,
                    "html": html,
                }
            )

        with patch("galaxy.util.send_mail", side_effect=validate_send_email) as mock_send_mail:
            notification_data = self._default_test_notification_data()

            # Send normal message notification
            self._send_message_notification_to_users([user], notification=notification_data)
            # The in-app notification should be sent but the email notification should not be sent after dispatching
            user_notifications = self.notification_manager.get_user_notifications(user)
            assert len(user_notifications) == 1
            self.notification_manager.dispatch_pending_notifications_via_channels()
            mock_send_mail.assert_not_called()

            # Send urgent message notification
            notification_data["variant"] = NotificationVariant.urgent
            self._send_message_notification_to_users([user], notification=notification_data)
            # The in-app notification should be sent, now there are 2 notifications
            user_notifications = self.notification_manager.get_user_notifications(user)
            assert len(user_notifications) == 2
            # The email notification should be sent after dispatching the pending notifications
            self.notification_manager.dispatch_pending_notifications_via_channels()
            mock_send_mail.assert_called_once()
            assert len(emails_sent) == 1


class TestNotificationRecipientResolver(NotificationsBaseTestCase):
    def test_default_resolution_strategy(self):
        recipients, expected_user_ids = self._create_test_recipients_scenario()
        resolver = NotificationRecipientResolver(strategy=DefaultStrategy(self.trans.sa_session))
        resolved_users = resolver.resolve(recipients)
        self._assert_resolved_match_expected_users(resolved_users, expected_user_ids)

    def _create_test_recipients_scenario(self):
        """Creates a slightly 'complex' hierarchy combination of groups and roles
        for testing recipient users resolution."""
        users = self._create_test_users(num_users=10)

        group1 = self._create_test_group(
            "Group1",
            users=[users[0], users[1]],
            roles=[],
        )
        role1 = self._create_test_role(
            "Role1",
            users=[users[3], users[5]],
            groups=[],
        )
        group2 = self._create_test_group(
            "Group2",
            users=[users[1], users[2]],
            roles=[role1],
        )
        role2 = self._create_test_role(
            "Role2",
            users=[users[4]],
            groups=[group2],
        )
        group3 = self._create_test_group(
            "Group3",
            users=[users[5]],
            roles=[role2],
        )
        role3 = self._create_test_role(
            "Role3",
            users=[users[7]],
            groups=[group1],
        )

        recipients = NotificationRecipients.model_construct(
            user_ids=[users[9].id],
            group_ids=[group3.id],
            role_ids=[role3.id],
        )

        expected_user_ids: Set[int] = {
            users[9].id,  # From direct recipients.user_ids
            users[5].id,  # From group3.user_ids
            users[4].id,  # -From role2.user_ids
            users[1].id,  # --From group2.user_ids
            users[2].id,  # --From group2.user_ids
            users[3].id,  # ---From role1.user_ids
            users[5].id,  # ---From role1.user_ids (duplicated)
            users[7].id,  # From role3.user_ids
            users[0].id,  # -From group1.user_ids
            users[1].id,  # -From group1.user_ids (duplicated)
        }

        return recipients, expected_user_ids

    def _assert_resolved_match_expected_users(self, resolved_users: List[User], expected_user_ids: Set[int]):
        assert len(resolved_users) == len(expected_user_ids)
        for user in resolved_users:
            assert user.id in expected_user_ids

    def _create_test_group(self, name: str, users: List[User], roles: List[Role]):
        sa_session = self.trans.sa_session
        group = Group(name=name)
        sa_session.add(group)
        user_ids = [user.id for user in users]
        role_ids = [role.id for role in roles]
        self.trans.app.security_agent.set_group_user_and_role_associations(group, user_ids=user_ids, role_ids=role_ids)
        return group

    def _create_test_role(self, name: str, users: List[User], groups: List[Group]):
        sa_session = self.trans.sa_session
        role = Role(name=name)
        sa_session.add(role)
        for user in users:
            self.trans.app.security_agent.associate_user_role(user, role)
        for group in groups:
            self.trans.app.security_agent.associate_group_role(group, role)
        sa_session.flush()
        return role
