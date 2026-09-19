import re

from ._framework import ApiTestCase

# Backbone, underscore and jQuery are no longer bundled as global objects for
# injected webhook scripts. These patterns catch webhook scripts that still rely
# on them (matching usage, not passing mentions in comments).
REMOVED_GLOBAL_PATTERNS = [
    re.compile(r"Backbone\."),
    re.compile(r"_\.(template|each|map|extend|isEmpty)\("),
    re.compile(r"\bjQuery\("),
    re.compile(r"\$\(document\)"),
]


class TestWebhooksApi(ApiTestCase):
    def setUp(self):
        super().setUp()

    def test_get_all(self):
        response = self._get("webhooks")

        self._assert_status_code_is(response, 200)
        webhook_objs = self._assert_are_webhooks(response)
        ids = self._get_webhook_ids(webhook_objs)
        for expected_id in [
            "history_test1",
            "history_test2",
            "masthead_test",
            "phdcomics",
            "trans_object",
            "xkcd",
            "gtn",
        ]:
            assert expected_id in ids

    def test_get_data(self):
        response = self._get("webhooks/trans_object/data")
        self._assert_status_code_is(response, 200)
        self._assert_has_keys(response.json(), "username")

    def test_scripts_avoid_removed_globals(self):
        response = self._get("webhooks")
        self._assert_status_code_is(response, 200)
        for webhook in response.json():
            script = webhook.get("script") or ""
            for pattern in REMOVED_GLOBAL_PATTERNS:
                assert not pattern.search(
                    script
                ), f"Webhook '{webhook.get('id')}' script uses removed global matching {pattern.pattern!r}"

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
