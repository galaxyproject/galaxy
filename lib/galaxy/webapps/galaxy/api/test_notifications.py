from typing import (
    List,
    Optional,
)

from galaxy_test.base.populators import DatasetPopulator
from ._framework import ApiTestCase


class NotificationsApiTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_index(self):
        notification_ids = [self.dataset_populator.notification_id()]
        payload = {
            "notification_id": notification_ids,
        }
        response = self._post("notifications", payload, admin=True, json=True)
        self._assert_status_code_is(response, 200)
        notifications = response.json()[0]  # POST /api/groups returns a list

        assert isinstance(notifications, list)
        assert len(notifications) > 0
