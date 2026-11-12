from urllib.parse import urljoin
from uuid import uuid4

import pytest
from requests import get

from galaxy_test.base.decorators import requires_new_published_objects
from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from ._framework import ApiTestCase

ANY_ORIGIN = "frame-ancestors *"
ONLY_GALAXY = "frame-ancestors 'self'"


class TestWidgetsApi(ApiTestCase):
    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_index(self):
        response = self._get("widgets", anon=True)
        self._assert_status_code_is(response, 200)
        assert {"history_graph", "page", "workflow"} <= {widget["id"] for widget in response.json()}

    @pytest.mark.parametrize(
        "path, frame_ancestors",
        [
            ("widgets/histories/1a/graph", ONLY_GALAXY),
            ("widgets/pages/1a", ONLY_GALAXY),
            ("widgets/workflows/1a", ONLY_GALAXY),
        ],
    )
    def test_widgets_app(self, path, frame_ancestors):
        self._assert_frame_ancestors(path, frame_ancestors)

    @requires_new_published_objects
    @pytest.mark.parametrize("widget", ["pages", "workflows"])
    def test_any_origin_frames_only_link_accessible_widgets(self, widget):
        item_id = self._create(widget)
        path = f"widgets/{widget}/{item_id}"
        self._assert_frame_ancestors(path, ONLY_GALAXY)
        other_user = self._setup_user(f"{uuid4()}@example.org")
        self._set_sharing(widget, item_id, "share_with_users", {"user_ids": [other_user["id"]]})
        self._assert_frame_ancestors(path, ONLY_GALAXY)
        self._set_sharing(widget, item_id, "enable_link_access")
        self._assert_frame_ancestors(path, ANY_ORIGIN)
        self._assert_frame_ancestors(f"{path}/", ANY_ORIGIN)
        self._set_sharing(widget, item_id, "publish")
        self._assert_frame_ancestors(path, ANY_ORIGIN)
        self._assert_status_code_is_ok(self._delete(f"{widget}/{item_id}"))
        self._assert_frame_ancestors(path, ONLY_GALAXY)

    @requires_new_published_objects
    @pytest.mark.parametrize(
        "path",
        [
            "widgets/pages/{id}/extra",
            "widgets/pages/{id}x",
            "widgets/pages%2F..%2Fpages/{id}",
            "widgets/pages/{id}%2F..%2F..%2Fhistories/{id}/graph",
        ],
    )
    def test_malformed_widget_paths_frame_only_galaxy(self, path):
        page_id = self._create("pages")
        self._set_sharing("pages", page_id, "publish")
        self._assert_frame_ancestors(f"widgets/pages/{page_id}", ANY_ORIGIN)
        self._assert_frame_ancestors(path.format(id=page_id), ONLY_GALAXY)

    def _create(self, widget: str) -> str:
        if widget == "pages":
            item_id = self.dataset_populator.new_page(slug=f"widget-{uuid4()}")["id"]
        else:
            item_id = self.workflow_populator.simple_workflow("widget")
        return item_id

    def _set_sharing(self, widget: str, item_id: str, action: str, payload: dict | None = None):
        response = self._put(f"{widget}/{item_id}/{action}", data=payload, json=True)
        self._assert_status_code_is_ok(response)

    def _assert_frame_ancestors(self, path: str, frame_ancestors: str):
        response = get(urljoin(self.url, path))
        self._assert_status_code_is(response, 200)
        assert "widgets.bundled.js" in response.text
        assert response.headers["Content-Security-Policy"] == frame_ancestors
        assert "X-Frame-Options" not in response.headers
