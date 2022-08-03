from galaxy_test.base.populators import DatasetPopulator
from ._framework import ApiTestCase


class NotificationsApiTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_index(self):
        print("Entering test")
        # payload = {
        #     "message": "Test Message"
        # }
        message = "Testt Message"
        notification_response = self._post("notifications", message_text=message, json=True)
        print(notification_response, " test message xx")
        assert notification_response.status_code == 200
        # notification_response = self._get("notifications", data=payload, json=True)
        assert notification_response.status_code == 200
        print(notification_response, " test gett")
        notifications = notification_response.json()[0]  # Get /api/notifications returns a list
        assert isinstance(notifications, list)
        assert len(notifications) > 0
