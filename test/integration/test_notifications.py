from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
)
from uuid import uuid4

from galaxy_test.driver.integration_util import IntegrationTestCase

NOTIFICATION_TEST_DATA = {
    "source": "integration_tests",
    "variant": "info",
    "category": "message",
    "content": {
        "category": "message",
        "subject": "Testing Subject",
        "message": "Testing Message",
    },
}

BROADCAST_NOTIFICATION_TEST_DATA = {
    "source": "integration_tests",
    "variant": "urgent",
    "category": "broadcast",
    "content": {
        "category": "broadcast",
        "subject": "Testing Broadcast",
        "message": "Testing Broadcast Message",
    },
}


class TestNotificationsIntegration(IntegrationTestCase):
    task_based = False
    framework_tool_and_types = False

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_notification_system"] = True

    def test_notification_status(self):
        user1 = self._create_test_user()
        user2 = self._create_test_user()

        before_creating_notifications = datetime.utcnow()

        # Only user1 will receive this notification
        created_response = self._send_test_notification_to([user1["id"]])
        assert created_response["total_notifications_sent"] == 1

        # Both user1 and user2 will receive this notification
        created_response = self._send_test_notification_to([user1["id"], user2["id"]])
        assert created_response["total_notifications_sent"] == 2

        # All users will receive this broadcasted notification
        notifications_status = self._send_broadcast_notification()
        assert notifications_status["total_notifications_sent"] == 1

        after_creating_notifications = datetime.utcnow()

        # The default user should have received only the broadcasted notifications
        status = self._get_notifications_status_since(before_creating_notifications)
        assert status["total_unread_count"] == 0
        assert len(status["notifications"]) == 0
        assert len(status["broadcasts"]) == 1

        with self._different_user(user1["email"]):
            status = self._get_notifications_status_since(before_creating_notifications)
            assert status["total_unread_count"] == 2
            assert len(status["notifications"]) == 2
            assert len(status["broadcasts"]) == 1
            # Mark one unseen notification as seen
            unseen_notification = status["notifications"][0]["id"]
            self._update_notification(unseen_notification, update_state={"seen": True})
            status = self._get_notifications_status_since(before_creating_notifications)
            # The total unread count should be updated
            assert status["total_unread_count"] == 1
            assert len(status["notifications"]) == 2
            assert len(status["broadcasts"]) == 1

        with self._different_user(user2["email"]):
            status = self._get_notifications_status_since(before_creating_notifications)
            assert status["total_unread_count"] == 1
            assert len(status["notifications"]) == 1
            assert len(status["broadcasts"]) == 1

            # Getting the notifications status since a posterior date does not return notifications
            # but the total number of unread notifications is maintained
            status = self._get_notifications_status_since(after_creating_notifications)
            assert status["total_unread_count"] == 1
            assert len(status["notifications"]) == 0
            assert len(status["broadcasts"]) == 0

    def test_user_cannot_access_other_users_notifications(self):
        user1 = self._create_test_user()
        user2 = self._create_test_user()

        created_response = self._send_test_notification_to([user1["id"]])
        notification_id = created_response["notification"]["id"]

        with self._different_user(user1["email"]):
            response = self._get(f"notifications/{notification_id}")
            self._assert_status_code_is_ok(response)

        with self._different_user(user2["email"]):
            response = self._get(f"notifications/{notification_id}")
            self._assert_status_code_is(response, 404)

    def test_delete_notification_by_user(self):
        user1 = self._create_test_user()
        user2 = self._create_test_user()

        before_creating_notifications = datetime.utcnow()

        created_response = self._send_test_notification_to([user1["id"], user2["id"]])
        assert created_response["total_notifications_sent"] == 2
        notification_id = created_response["notification"]["id"]

        with self._different_user(user1["email"]):
            response = self._get(f"notifications/{notification_id}")
            self._assert_status_code_is_ok(response)
            self._delete(f"notifications/{notification_id}")
            # After delete, it is no longer available for this user
            response = self._get(f"notifications/{notification_id}")
            self._assert_status_code_is(response, 404)
            status = self._get_notifications_status_since(before_creating_notifications)
            assert status["total_unread_count"] == 0
            assert len(status["notifications"]) == 0
            assert len(status["broadcasts"]) == 0

        with self._different_user(user2["email"]):
            response = self._get(f"notifications/{notification_id}")
            self._assert_status_code_is_ok(response)

    def _create_test_user(self):
        user = self._setup_user(f"{uuid4()}@galaxy.test")
        return user

    def _get_notifications_status_since(self, since: datetime):
        status_response = self._get(f"notifications/status?since={since}")
        self._assert_status_code_is_ok(status_response)
        status = status_response.json()
        return status

    def _send_test_notification_to(self, user_ids: List[str]):
        request = {
            "recipients": {"user_ids": user_ids},
            "notification": NOTIFICATION_TEST_DATA,
        }
        response = self._post("notifications", data=request, admin=True, json=True)
        self._assert_status_code_is_ok(response)
        created_response = response.json()
        return created_response

    def _send_broadcast_notification(self):
        response = self._post("notifications/broadcast", data=BROADCAST_NOTIFICATION_TEST_DATA, admin=True, json=True)
        self._assert_status_code_is_ok(response)
        notifications_status = response.json()
        return notifications_status

    def _update_notification(self, notification_id: str, update_state: Dict[str, Any]):
        update_response = self._put(f"notifications/{notification_id}", data=update_state, json=True)
        self._assert_status_code_is(update_response, 204)
