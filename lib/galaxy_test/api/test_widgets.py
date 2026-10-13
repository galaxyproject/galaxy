from ._framework import ApiTestCase


class TestWidgetsApi(ApiTestCase):
    def test_index(self):
        response = self._get("widgets", anon=True)
        self._assert_status_code_is(response, 200)
        assert "history_graph" in [widget["id"] for widget in response.json()]
