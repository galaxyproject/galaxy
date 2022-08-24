from galaxy_test.base.populators import DatasetPopulator
from ._framework import ApiTestCase


class NotificationsApiTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_index(self):
        encoded_user_id = self.dataset_populator.user_id()
        create_notification_payload = {"message_text": "Test Message", "user_ids": [encoded_user_id]}
        notification_response = self._post("notifications", create_notification_payload, json=True, admin=True)
        notification_response.raise_for_status()
        notification_list_parameters = {"limit": 5, "offset": 0}
        notification_response = self._get("notifications", notification_list_parameters)
        notification_response.raise_for_status()
        notifications = notification_response.json()  # Get /api/notifications returns a list
        assert isinstance(notifications, list)
        assert len(notifications) > 0

    def test_create(self):
        encoded_user_id = self.dataset_populator.user_id()
        create_notification_payload = {"message_text": "Test Message", "user_ids": [encoded_user_id]}
        notification_response = self._post("notifications", create_notification_payload, json=True, admin=True)
        notification_response.raise_for_status()
        notification = notification_response.json()
        assert notification["id"] is not None
        assert notification["message_text"] == "Test Message"

    def test_show(self):
        encoded_user_id = self.dataset_populator.user_id()
        create_notification_payload = {"message_text": "Test Message", "user_ids": [encoded_user_id]}
        notification_response = self._post("notifications", create_notification_payload, json=True, admin=True)
        notification_response.raise_for_status()
        notification = notification_response.json()
        notification_response = self._get(f"notifications/{notification['id']}")
        notification_response.raise_for_status()
        notification = notification_response.json()
        assert notification["id"] is not None
        assert notification["message_text"] is not None

    def test_update(self):
        encoded_user_id = self.dataset_populator.user_id()
        create_notification_payload = {"message_text": "Test Message", "user_ids": [encoded_user_id]}
        notification_response = self._post("notifications", create_notification_payload, json=True, admin=True)
        notification_response.raise_for_status()
        notification = notification_response.json()
        create_update_payload = {"message_text": "New Message"}
        notification_id = notification["id"]
        notification_response = self._put(f"notifications/{notification_id}", create_update_payload, json=True)
        notification_response.raise_for_status()
        notification = notification_response.json()
        assert notification["message_text"] == "New Message"
    
    # def test_update_status(self):
    #     encoded_user_id = self.dataset_populator.user_id()
    #     create_notification_payload = {"message_text": "Test Message", "user_ids": [encoded_user_id]}
    #     notification_response = self._post("notifications", create_notification_payload, json=True, admin=True)
    #     notification_response.raise_for_status()
    #     notification = notification_response.json()
    #     create_update_payload = {"status_seen": True}
    #     notification_id = notification["id"]
    #     notification_response = self._put(f"notifications/{notification_id}", create_update_payload, json=True)
    #     notification_response.raise_for_status()
    #     notification = notification_response.json()
    #     assert notification["message_text"] == "New Message"
