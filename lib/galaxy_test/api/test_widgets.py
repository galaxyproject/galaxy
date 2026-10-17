from urllib.parse import urljoin

from requests import get

from ._framework import ApiTestCase


class TestWidgetsApi(ApiTestCase):
    def test_index(self):
        response = self._get("widgets", anon=True)
        self._assert_status_code_is(response, 200)
        assert "history_graph" in [widget["id"] for widget in response.json()]

    def test_widgets_app(self):
        response = get(urljoin(self.url, "widgets/histories/1a/graph"))
        self._assert_status_code_is(response, 200)
        assert "widgets.bundled.js" in response.text
        assert response.headers["Content-Security-Policy"] == "frame-ancestors 'self'"
        assert "X-Frame-Options" not in response.headers
