from galaxy_test.base.populators import DatasetPopulator
from ._framework import ApiTestCase


class NotificationsApiTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_index(self):
        payload = {"message_text": "Test Message"}
        notification_response = self._post("notifications", payload, json=True)
        print(notification_response, " test noti")
        notification = notification_response.json()[0]
        notification_response = self._get("notifications", json=True)
        assert notification_response.status_code == 200
        print(notification_response, " test gett")
        notifications = notification_response.json()[0]  # Get /api/notifications returns a list
        assert isinstance(notifications, list)
        assert len(notifications) > 0
