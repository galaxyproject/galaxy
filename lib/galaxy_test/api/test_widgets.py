from urllib.parse import urljoin

import pytest
from requests import get

from ._framework import ApiTestCase


class TestWidgetsApi(ApiTestCase):
    def test_index(self):
        response = self._get("widgets", anon=True)
        self._assert_status_code_is(response, 200)
        assert {"history_graph", "page", "workflow", "visualization"} <= {widget["id"] for widget in response.json()}

    @pytest.mark.parametrize(
        "path, frame_ancestors",
        [
            ("widgets/histories/1a/graph", "frame-ancestors 'self'"),
            ("widgets/pages/1a", "frame-ancestors *"),
            ("widgets/workflows/1a", "frame-ancestors *"),
            ("widgets/visualizations/1a", "frame-ancestors 'self'"),
        ],
    )
    def test_widgets_app(self, path, frame_ancestors):
        response = get(urljoin(self.url, path))
        self._assert_status_code_is(response, 200)
        assert "widgets.bundled.js" in response.text
        assert response.headers["Content-Security-Policy"] == frame_ancestors
        assert "X-Frame-Options" not in response.headers
