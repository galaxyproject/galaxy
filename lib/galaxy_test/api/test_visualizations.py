import uuid

from galaxy_test.api.sharable import SharingApiTests
from galaxy_test.base.api_asserts import assert_has_keys
from ._framework import ApiTestCase

INDEX_KEYS = ["id", "title", "type", "dbkey"]
SHOW_KEYS = INDEX_KEYS + ["user_id", "model_class", "revisions", "latest_revision", "annotation"]
REVISION_KEYS = ["id", "title", "visualization_id", "dbkey", "model_class", "config"]


class TestVisualizationsApi(ApiTestCase, SharingApiTests):
    api_name = "visualizations"

    def create(self, _: str) -> str:
        viz_id, _ = self._create_viz()
        return viz_id

    def test_index_and_show(self):
        self._create_viz()  # to ensure on exists to index
        index = self._get("visualizations").json()
        assert len(index) >= 1
        for viz in index:
            self._verify_viz_object(viz, show=False)
        first_viz = index[0]
        self._show_viz(first_viz["id"])

    def test_index_ordering(self):
        ids = []
        for x in range(3):
            v = self._new_viz(title=f"visualization-order-{x}", slug=f"slug-order-{x}").json()
            ids.append(v["id"])
        index_ids = self._index_ids()
        for x in range(2):
            assert index_ids.index(ids[x]) > index_ids.index(ids[x + 1])
        index_ids = self._index_ids(dict(sort_desc=False))
        for x in range(2):
            assert index_ids.index(ids[x]) < index_ids.index(ids[x + 1])

    def test_index_filtering(self):
        ids = []
        for x in range(3):
            v = self._new_viz(title=f"visualization-filter-{x}", slug=f"slug-filter-{x}").json()
            ids.append(v["id"])
        index_ids = self._index_ids(dict(show_own=False))
        for x in range(3):
            assert ids[x] not in index_ids
        self._publish_viz(ids[0])
        index_ids = self._index_ids(dict(show_own=False))
        assert ids[0] in index_ids
        index_ids = self._index_ids(dict(show_own=False, show_published=False))
        for x in range(3):
            assert ids[x] in index_ids
        index_ids = self._index_ids(dict(search="visualization-filter-1"))
        assert ids[1] in index_ids
        self._update_viz(ids[1], dict(deleted=True))
        index_ids = self._index_ids(dict(search="visualization-filter-1"))
        assert ids[1] not in index_ids
        index_ids = self._index_ids(dict(search="is:deleted", show_published=False))
        assert ids[1] in index_ids

    def test_create(self):
        viz_id, viz_request = self._create_viz()
        self._show_viz(viz_id, assert_ok=True)

    def test_create_fails_without_title(self):
        response = self._new_viz(title="")
        self._assert_status_code_is(response, 400)

    def test_create_fails_with_bad_slug(self):
        response = self._new_viz(slug="123_()")
        self._assert_status_code_is(response, 400)

    def test_create_fails_with_invalid_config(self):
        response = self._new_viz(config="3 = nime")
        self._assert_status_code_is(response, 400)

    def test_sharing(self):
        viz_id, _ = self._create_viz()
        sharing_response = self._get(f"visualizations/{viz_id}/sharing")
        self._assert_status_code_is(sharing_response, 200)
        self._assert_has_keys(
            sharing_response.json(), "title", "importable", "id", "username_and_slug", "published", "users_shared_with"
        )

    def test_update_title(self):
        viz_id, viz = self._create_viz()
        update_url = self._api_url(f"visualizations/{viz_id}", use_key=True)
        response = self._put(update_url, {"title": "New Name"}, json=True)
        self._assert_status_code_is(response, 200)
        updated_viz = self._show_viz(viz_id)
        assert updated_viz["title"] == "New Name"

    def _create_viz(self, **kwds):
        response = self._new_viz(**kwds)
        self._assert_status_code_is(response, 200)
        viz = response.json()
        return viz["id"], viz

    def _index(self, params):
        index_response = self._get("visualizations", data=params or {})
        return index_response.json()

    def _index_ids(self, params=None):
        return [entry["id"] for entry in self._index(params)]

    def _new_viz(self, title=None, slug=None, config=None):
        uuid_str = str(uuid.uuid4())
        title = title if title is not None else "Test Visualization"
        slug = slug if slug is not None else f"test-visualization-{uuid_str}"
        config = (
            config
            if config is not None
            else {
                "x": 10,
                "y": 12,
            }
        )
        create_payload = {
            "title": title,
            "slug": slug,
            "type": "example",
            "dbkey": "hg17",
            "annotation": "this is a test of the emergency visualization system",
            "config": config,
        }
        response = self._post("visualizations", data=create_payload, json=True)
        return response

    def _publish_viz(self, id):
        sharing_response = self._put(f"visualizations/{id}/publish")
        assert sharing_response.status_code == 200
        return sharing_response.json()

    def _show_viz(self, viz_id, assert_ok=True):
        show_response = self._get(f"visualizations/{viz_id}")
        if assert_ok:
            self._assert_status_code_is(show_response, 200)
        viz = show_response.json()
        if assert_ok:
            self._verify_viz_object(viz, show=True)
        return viz

    def _update_viz(self, viz_id, params=None):
        response = self._put(f"visualizations/{viz_id}", params or {}, json=True)
        self._assert_status_code_is(response, 200)
        return response

    def _verify_viz_object(self, obj, show=False):
        assert_has_keys(obj, *(SHOW_KEYS if show else INDEX_KEYS))
        if show:
            assert "revisions" in obj
            revisions = obj["revisions"]
            assert len(revisions) >= 1
            assert "latest_revision" in obj
            latest_revision = obj["latest_revision"]
            assert_has_keys(latest_revision, *REVISION_KEYS)
            assert latest_revision["model_class"] == "VisualizationRevision"
            assert latest_revision["id"] in revisions
