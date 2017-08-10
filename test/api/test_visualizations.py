import json
import uuid

from requests import (
    put
)

from base import api
from base.api_asserts import assert_has_keys

INDEX_KEYS = [
    'id', 'title', 'type', 'dbkey', 'url'
]
SHOW_KEYS = INDEX_KEYS + [
    'user_id', 'model_class', 'revisions', 'latest_revision', 'annotation'
]
REVISION_KEYS = [
    'id', 'title', 'visualization_id', 'dbkey', 'model_class', 'config'
]


class VisualizationsApiTestCase( api.ApiTestCase ):

    def test_index_and_show(self):
        self._create_viz()  # to ensure on exists to index
        index = self._get("visualizations").json()
        assert len(index) >= 1
        for viz in index:
            self._verify_viz_object(viz, show=False)
        first_viz = index[0]
        self._show_viz(first_viz["id"])

    def test_create(self):
        viz_id, viz_request = self._create_viz()
        self._show_viz(viz_id, assert_ok=True)

    def test_create_fails_without_title(self):
        response = self._raw_create_viz(title='')
        self._assert_status_code_is(response, 400)

    def test_create_fails_with_bad_slug(self):
        response = self._raw_create_viz(slug='123_()')
        self._assert_status_code_is(response, 400)

    def test_create_fails_with_invalid_config(self):
        response = self._raw_create_viz(config="3 = nime")
        self._assert_status_code_is(response, 400)

    def test_update_title(self):
        viz_id, viz = self._create_viz()
        update_url = self._api_url("visualizations/%s" % viz_id, use_key=True)
        response = put(update_url, {"title": "New Name"})
        self._assert_status_code_is(response, 200)
        updated_viz = self._show_viz(viz_id)
        assert updated_viz["title"] == "New Name"

    def _show_viz(self, viz_id, assert_ok=True):
        show_response = self._get("visualizations/%s" % viz_id)
        if assert_ok:
            self._assert_status_code_is(show_response, 200)

        viz = show_response.json()

        if assert_ok:
            self._verify_viz_object(viz, show=True)

        return viz

    def _raw_create_viz(self, title=None, slug=None, config=None):
        uuid_str = str(uuid.uuid4())

        title = title if title is not None else 'Test Visualization'
        slug = slug if slug is not None else 'test-visualization-%s' % uuid_str
        config = config if config is not None else json.dumps({
            "x": 10,
            "y": 12,
        })
        create_payload = {
            "title": title,
            "slug": slug,
            "type": 'test',
            "dbkey": 'hg17',
            "annotation": 'this is a test of the emergency visualization system',
            "config": config,
        }
        response = self._post("visualizations", data=create_payload)
        return response

    def _create_viz(self, **kwds):
        response = self._raw_create_viz(**kwds)
        self._assert_status_code_is(response, 200)
        viz = response.json()
        return viz["id"], viz

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
