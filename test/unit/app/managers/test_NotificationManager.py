import json
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
    ActionLink,
    BroadcastNotificationContent,
    BroadcastNotificationCreateRequest,
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

default_password = "123456"


class NotificationsBaseTestCase(BaseTestCase):
    def _create_test_user(self, username="user1") -> User:
        user_data = dict(email=f"{username}@user.email", username=username, password=default_password)
        user = self.user_manager.create(**user_data)
        return user

    def _create_test_users(self, num_users: int = 1) -> List[User]:
        users = [self._create_test_user(f"username{num:02}") for num in range(num_users)]
        return users

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


class NotificationManagerBaseTestCase(NotificationsBaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.notification_manager = NotificationManager(self.trans.sa_session, self.app.config)


class TestBroadcastNotifications(NotificationManagerBaseTestCase):
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


class TestUserNotifications(NotificationManagerBaseTestCase):
    def test_create_notification_for_users(self):
        num_target_users = 2
        users = self._create_test_users(num_users=num_target_users)
        expected_notification = self._default_test_notification_data()
        expected_notification.update(
            {
                "source": "test_create_notification_for_users",
                "publication_time": datetime.utcnow() + timedelta(hours=24),
            }
        )
        actual_notification, actual_notifications_sent = self._send_message_notification_to_users(
            users, notification=expected_notification
        )

        assert actual_notifications_sent == num_target_users
        self._assert_notification_is_as_expected(actual_notification, expected_notification)

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

        self._assert_notification_is_as_expected(actual_user_notification, expected_user_notification)
        assert actual_user_notification["seen_time"] is None
        assert actual_user_notification["favorite"] is False
        assert actual_user_notification["deleted"] is False

    def test_update_user_notifications(self):
        user = self._create_test_user()
        notification, _ = self._send_message_notification_to_users([user])
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
        user = self._create_test_user()
        default_preferences = UserNotificationPreferences.default()

        preferences = self.notification_manager.get_user_notification_preferences(user)

        assert preferences == default_preferences

    def test_update_user_notification_preferences(self):
        user = self._create_test_user()
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
        user = self._create_test_user()
        now = datetime.utcnow()
        notification, _ = self._send_message_notification_to_users([user], notification={"expiration_time": now})
        user_notification = self.notification_manager.get_user_notification(user, notification.id, active_only=False)
        assert user_notification
        assert self._has_expired(user_notification.expiration_time) is True

        self.notification_manager.cleanup_expired_notifications()

        with pytest.raises(ObjectNotFound):
            self.notification_manager.get_user_notification(user, notification.id, active_only=False)

    def test_cleanup_keeps_expired_favorite_notifications_until_deleted(self):
        user = self._create_test_user()
        now = datetime.utcnow()
        notification, _ = self._send_message_notification_to_users([user], notification={"expiration_time": now})
        request = UserNotificationUpdateRequest(favorite=True)
        self.notification_manager.update_user_notifications(user, set([notification.id]), request)
        user_notification = self.notification_manager.get_user_notification(user, notification.id, active_only=False)
        assert self._has_expired(user_notification.expiration_time) is True
        assert user_notification.favorite is True

        self.notification_manager.cleanup_expired_notifications()

        # The notification should remain
        user_notification = self.notification_manager.get_user_notification(user, notification.id, active_only=False)
        assert user_notification

        # Mark it as deleted
        request = UserNotificationUpdateRequest(deleted=True)
        self.notification_manager.update_user_notifications(user, set([notification.id]), request)
        user_notification = self.notification_manager.get_user_notification(user, notification.id, active_only=False)
        assert user_notification.favorite is True
        assert user_notification.deleted is True

        self.notification_manager.cleanup_expired_notifications()

        # If marked as deleted it will be removed (even if marked as favorite)
        with pytest.raises(ObjectNotFound):
            self.notification_manager.get_user_notification(user, notification.id, active_only=False)

    def test_users_do_not_receive_opt_out_notifications(self):
        users = self._create_test_users(num_users=2)
        user_a = users[0]
        user_b = users[1]
        update_request = UpdateUserNotificationPreferencesRequest(
            preferences=UserNotificationPreferences(
                __root__={
                    PersonalNotificationCategory.message: NotificationCategorySettings(enabled=False),
                }
            )
        )
        self.notification_manager.update_user_notification_preferences(user_a, update_request)
        self._send_message_notification_to_users(users)

        user_notifications = self.notification_manager.get_user_notifications(user_a)
        assert len(user_notifications) == 0
        user_notifications = self.notification_manager.get_user_notifications(user_b)
        assert len(user_notifications) == 1

    def _send_message_notification_to_users(self, users: List[User], notification: Optional[Dict[str, Any]] = None):
        data = self._default_test_notification_data()
        if notification:
            data.update(notification)
        notification_data = NotificationCreateData(**data)

        request = NotificationCreateRequest(
            recipients=NotificationRecipients.construct(
                user_ids=[user.id for user in users],
            ),
            notification=notification_data,
        )
        created_notification, notifications_sent = self.notification_manager.send_notification_to_recipients(request)
        return created_notification, notifications_sent

    def _has_expired(self, expiration_time: Optional[datetime]) -> bool:
        return expiration_time < datetime.utcnow() if expiration_time else False

    def _assert_notification_is_as_expected(self, actual_notification: Any, expected_notification: Dict[str, Any]):
        assert actual_notification
        assert actual_notification.id
        assert actual_notification.source == expected_notification["source"]
        assert actual_notification.variant == expected_notification["variant"]
        assert actual_notification.category == expected_notification["category"]

        expected_publication_time = expected_notification.get("publication_time")
        if expected_publication_time:
            assert actual_notification.publication_time == expected_publication_time
        else:
            assert actual_notification.publication_time is not None

        expected_expiration_time = expected_notification.get("expiration_time")
        if expected_expiration_time:
            assert actual_notification.expiration_time == expected_expiration_time
        else:
            assert actual_notification.expiration_time is not None

        assert actual_notification.content
        user_notification_content = json.loads(actual_notification.content)
        assert user_notification_content["category"] == expected_notification["content"]["category"]
        assert user_notification_content["subject"] == expected_notification["content"]["subject"]
        assert user_notification_content["message"] == expected_notification["content"]["message"]


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

        recipients = NotificationRecipients.construct(
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
        with sa_session.begin():
            group = Group(name=name)
            sa_session.add(group)
            self.trans.app.security_agent.set_entity_group_associations(groups=[group], roles=roles, users=users)
            return group

    def _create_test_role(self, name: str, users: List[User], groups: List[Group]):
        sa_session = self.trans.sa_session
        with sa_session.begin():
            role = Role(name=name)
            sa_session.add(role)
            for user in users:
                self.trans.app.security_agent.associate_user_role(user, role)
            for group in groups:
                self.trans.app.security_agent.associate_group_role(group, role)
            return role
