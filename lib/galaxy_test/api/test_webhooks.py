from ._framework import ApiTestCase


class WebhooksApiTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()

    def test_get_all(self):
        response = self._get("webhooks")

        self._assert_status_code_is(response, 200)
        webhook_objs = self._assert_are_webhooks(response)
        ids = self._get_webhook_ids(webhook_objs)
        for expected_id in ["history_test1", "history_test2", "masthead_test", "phdcomics", "trans_object", "xkcd"]:
            assert expected_id in ids

    def test_get_data(self):
        response = self._get("webhooks/trans_object/data")
        self._assert_status_code_is(response, 200)
        self._assert_has_keys(response.json(), "username")

    def _assert_are_webhooks(self, response):
        response_list = response.json()
        assert isinstance(response_list, list)
        for obj in response_list:
            self._assert_is_webhook(obj)
        return response_list

    def _assert_is_webhook(self, obj):
        assert isinstance(obj, dict)
        self._assert_has_keys(obj, "id", "type", "activate", "weight", "script", "styles", "config")

    def _get_webhook_ids(self, webhook_objs):
        names = [w.get("id") for w in webhook_objs]
        return names
