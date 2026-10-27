from urllib.parse import urljoin

import pytest
from requests import get

from ._framework import ApiTestCase


class TestWidgetsApi(ApiTestCase):
    def test_index(self):
        response = self._get("widgets", anon=True)
        self._assert_status_code_is(response, 200)
        assert {"history_graph", "page", "workflow"} <= {widget["id"] for widget in response.json()}

    @pytest.mark.parametrize("path", ["widgets/histories/1a/graph", "widgets/pages/1a", "widgets/workflows/1a"])
    def test_widgets_app(self, path):
        response = get(urljoin(self.url, path))
        self._assert_status_code_is(response, 200)
        assert "widgets.bundled.js" in response.text
        assert response.headers["Content-Security-Policy"] == "frame-ancestors *"
        assert "X-Frame-Options" not in response.headers
