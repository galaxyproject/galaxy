import os

from base import api
from galaxy.app import app
from galaxy.util import galaxy_root_path
from galaxy.webhooks import WebhooksRegistry

WEBHOOKS_DEMO_DIRECTORY = os.path.join(
    galaxy_root_path, 'config', 'plugins', 'webhooks', 'demo',
)


class WebhooksApiTestCase(api.ApiTestCase):
    def setUp(self):
        super(WebhooksApiTestCase, self).setUp()
        app.webhooks_registry = WebhooksRegistry(WEBHOOKS_DEMO_DIRECTORY)

    def test_get_all(self):
        response = self._get('webhooks')
        webhooks = [wh.to_dict() for wh in app.webhooks_registry.webhooks]

        self._assert_status_code_is(response, 200)
        self.assertEqual(response.json(), webhooks)

    def test_get_random(self):
        response = self._get('webhooks/tool')
        self._assert_status_code_is(response, 200)

    def test_get_all_by_type(self):
        webhook_type = 'tool'
        response = self._get('webhooks/%s/all' % webhook_type)
        webhooks = [
            wh.to_dict()
            for wh in app.webhooks_registry.webhooks
            if webhook_type in wh.type
        ]

        self._assert_status_code_is(response, 200)
        self.assertEqual(response.json(), webhooks)

    def test_get_data(self):
        response = self._get('webhooks/trans_object/get_data')
        self._assert_status_code_is(response, 200)
        self._assert_has_keys(response.json(), 'username')
