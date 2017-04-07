
from base import api
from base.driver_util import TEST_WEBHOOKS_DIR
from galaxy.webhooks import WebhooksRegistry


class WebhooksApiTestCase(api.ApiTestCase):

    def setUp(self):
        super(WebhooksApiTestCase, self).setUp()
        self.webhooks_registry = WebhooksRegistry(TEST_WEBHOOKS_DIR)

    def test_get_all(self):
        response = self._get('webhooks')

        self._assert_status_code_is(response, 200)
        webhook_objs = self._assert_are_webhooks(response)
        names = self._get_webhook_names(webhook_objs)
        for expected_name in ["history_test1", "history_test2", "masthead_test", "phdcomics", "trans_object", "xkcd"]:
            assert expected_name in names

    def test_get_random(self):
        response = self._get('webhooks/tool')
        self._assert_status_code_is(response, 200)
        self._assert_is_webhook(response.json())

    def test_get_all_by_type(self):
        # Ensure tool type filtering include a valid webhook of type tool and excludes a webhook
        # that isn't of type tool.
        response = self._get('webhooks/tool/all')

        self._assert_status_code_is(response, 200)
        webhook_objs = self._assert_are_webhooks(response)
        names = self._get_webhook_names(webhook_objs)
        assert "phdcomics" in names
        assert "trans_object" not in names  # properly filtered out by type

    def test_get_data(self):
        response = self._get('webhooks/trans_object/get_data')
        self._assert_status_code_is(response, 200)
        self._assert_has_keys(response.json(), 'username')

    def _assert_are_webhooks(self, response):
        response_list = response.json()
        assert isinstance(response_list, list)
        for obj in response_list:
            self._assert_is_webhook(obj)
        return response_list

    def _assert_is_webhook(self, obj):
        assert isinstance(obj, dict)
        self._assert_has_keys(obj, 'styles', 'activate', 'name', 'script', 'type', 'config')

    def _get_webhook_names(self, webhook_objs):
        names = [w.get("name") for w in webhook_objs]
        return names
