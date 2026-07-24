"""Integration tests for the curated workflows catalog (``GET /api/workflows/curated``).

Every case in this module is network-free, and deliberately so: the feature's
one outbound request (the IWC manifest download) must never fire from a test.
Two things guarantee that. The base class replaces both
``galaxy.workflow.curated.refresh_projection`` and
``galaxy.workflow.iwc_manifest.download_manifest`` with functions that raise, so any code
path that tries to fetch fails loudly instead of reaching the internet, and
every test asserts the download stub was never called. The catalog case gets
its data from a projection file written to ``curated_workflows_path`` before
Galaxy starts, which is exactly what the celery task would have produced.
"""

import os
from time import (
    monotonic,
    sleep,
)
from typing import (
    Any,
    ClassVar,
)
from unittest.mock import patch
from urllib.parse import urljoin
from uuid import uuid4

import requests

from galaxy.exceptions import error_codes
from galaxy.model import StoredWorkflow
from galaxy.model.item_attrs import add_item_annotation
from galaxy.workflow import (
    curated,
    iwc_manifest,
)
from galaxy_test.base import api_asserts
from galaxy_test.base.populators import WorkflowPopulator
from galaxy_test.driver import integration_util

# ``GalaxyInteractor.ensure_user_with_email`` derives the username from the
# email by replacing every character outside ``[a-z0-9-]`` with ``--``. The
# tests assert the derivation still holds before relying on it, so a change to
# that rule fails with a readable message rather than an empty result set.
CURATED_OWNER_EMAIL = "curatedowner@bx.psu.edu"
CURATED_OWNER_USERNAME = "curatedowner--bx--psu--edu"
# Username contains CURATED_OWNER_USERNAME as a substring. A configured owner
# list matched with ``ilike('%name%')`` instead of an exact ``in_()`` would
# wrongly pull this account's published workflows onto the curated tab.
MIRROR_OWNER_EMAIL = "xcuratedowner@bx.psu.edu"
MIRROR_OWNER_USERNAME = "xcuratedowner--bx--psu--edu"
MALICIOUS_ANNOTATION = '<img src=x onerror="alert(1)"><script>alert(2)</script>Safe text'


DOCKSTORE_TRS_TOOLS = "https://dockstore.org/api/ga4gh/trs/v2/tools"


def _catalog_entry(slug: str, name: str, tags: list[str], updated: str) -> dict[str, Any]:
    """Build one projected catalog row in the shape ``project_manifest`` emits."""
    return {
        "id": slug,
        "name": name,
        "description": "Example curated workflow.",
        "tags": tags,
        "collections": ["examples"],
        "number_of_steps": 4,
        "update_time": updated,
        "release": "0.1",
        "doi": "10.0000/zenodo.0000000",
        "external_url": f"https://iwc.galaxyproject.org/workflow/{slug}/",
        "owner": None,
        "stored_workflow_id": None,
        "trs_url": f"{DOCKSTORE_TRS_TOOLS}/%23workflow%2Fgithub.com%2Fiwc-workflows%2F{slug}%2Fmain/versions/v0.1",
        "trs_fallback_url": f"{DOCKSTORE_TRS_TOOLS}/%23workflow%2Fgithub.com%2Fiwc-workflows%2F{slug}%2Fmain/versions/main",
    }


# Ordered newest-first, which is the endpoint's default sort, so the expected
# pagination order is just this list.
CATALOG_ENTRIES = [
    _catalog_entry("assembly-hifi", "HiFi genome assembly", ["assembly"], "2024-05-01T00:00:00"),
    _catalog_entry("assembly-flye", "Flye long read assembly", ["assembly"], "2024-04-01T00:00:00"),
    _catalog_entry("variant-calling", "Variant calling", ["variants"], "2024-03-01T00:00:00"),
    _catalog_entry("rnaseq-counts", "RNA-seq counts", ["transcriptomics"], "2024-02-01T00:00:00"),
    _catalog_entry("chipseq-peaks", "ChIP-seq peaks", ["epigenetics"], "2024-01-01T00:00:00"),
]
CATALOG_IDS = [entry["id"] for entry in CATALOG_ENTRIES]


class _CuratedWorkflowsTestCase(integration_util.IntegrationTestCase):
    """Shared scaffolding, including the no-network guarantee."""

    def setUp(self):
        super().setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)
        curated.clear_caches()

        self._download_patch = patch.object(
            iwc_manifest,
            "download_manifest",
            side_effect=AssertionError("curated workflow tests must never contact iwc.galaxyproject.org"),
        )
        self.download_mock = self._download_patch.start()

        self._refresh_patch = patch.object(
            curated,
            "refresh_projection",
            side_effect=RuntimeError("curated catalog refresh is disabled in tests"),
        )
        self.refresh_mock = self._refresh_patch.start()

    def tearDown(self):
        try:
            # Drain any background refresh thread before the patches come off --
            # a thread that outlived the test would otherwise reach the real
            # fetcher. The network assertion runs last, once every thread the
            # test could have started is known to have finished.
            self._wait_for_refresh_to_settle()
            self._refresh_patch.stop()
            self._download_patch.stop()
            self._assert_no_network_access()
        finally:
            super().tearDown()

    def _assert_no_network_access(self) -> None:
        self.download_mock.assert_not_called()

    @staticmethod
    def _wait_for_refresh_to_settle(timeout: float = 30.0) -> None:
        # Reads private module state on purpose: the flag flips to False only
        # after the background thread has finished with ``refresh_projection``,
        # which is precisely the condition that makes unpatching safe.
        deadline = monotonic() + timeout
        while curated._refresh_in_flight and monotonic() < deadline:
            sleep(0.05)

    def _curated_response(self, anon: bool = False, **params: Any):
        return self._get("workflows/curated", data=params or None, anon=anon)

    def _curated_index(self, anon: bool = False, **params: Any) -> dict[str, Any]:
        response = self._curated_response(anon=anon, **params)
        api_asserts.assert_status_code_is(response, 200)
        return response.json()


class TestCuratedWorkflowsLocal(_CuratedWorkflowsTestCase):
    """``curated_workflows_source: local``: the tab lists the owners' published workflows."""

    published_ids: ClassVar[list[str]] = []
    published_names: ClassVar[list[str]] = []
    unpublished_id: ClassVar[str] = ""
    mirror_id: ClassVar[str] = ""
    token: ClassVar[str] = ""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["curated_workflows_source"] = "local"
        config["curated_workflow_owners"] = CURATED_OWNER_USERNAME

    def setUp(self):
        super().setUp()
        if not TestCuratedWorkflowsLocal.published_ids:
            self._create_fixtures()

    def _create_fixtures(self) -> None:
        fixtures = TestCuratedWorkflowsLocal
        token = fixtures.token = uuid4().hex

        owner, _ = self._setup_user_get_key(CURATED_OWNER_EMAIL)
        owner_detail = self._get(f"users/{owner['id']}", admin=True).json()
        assert owner_detail["username"] == CURATED_OWNER_USERNAME, (
            f"Test user {CURATED_OWNER_EMAIL} got username {owner_detail['username']}, expected "
            f"{CURATED_OWNER_USERNAME} -- the curated owner allowlist in handle_galaxy_config_kwds is stale."
        )

        fixtures.published_names = [f"{prefix}curated {token}" for prefix in ("a", "b", "c")]
        with self._different_user(CURATED_OWNER_EMAIL):
            fixtures.published_ids = [
                self.workflow_populator.simple_workflow(name, publish=True) for name in fixtures.published_names
            ]
            # The first tag is a strict prefix of the second, so quoted and
            # unquoted tag searches have to disagree.
            self.workflow_populator.set_tags(fixtures.published_ids[0], [f"curatedtag{token}"])
            self.workflow_populator.set_tags(fixtures.published_ids[1], [f"curatedtag{token}longer"])
            fixtures.unpublished_id = self.workflow_populator.simple_workflow(f"dcurated {token}")
        self._store_raw_annotation(fixtures.published_ids[2], MALICIOUS_ANNOTATION)

        mirror, _ = self._setup_user_get_key(MIRROR_OWNER_EMAIL)
        mirror_detail = self._get(f"users/{mirror['id']}", admin=True).json()
        assert mirror_detail["username"] == MIRROR_OWNER_USERNAME
        assert CURATED_OWNER_USERNAME in MIRROR_OWNER_USERNAME, (
            "The mirror account must contain the curated owner's username as a substring for this "
            "test to pin exact-match owner filtering."
        )
        with self._different_user(MIRROR_OWNER_EMAIL):
            fixtures.mirror_id = self.workflow_populator.simple_workflow(f"mcurated {token}", publish=True)

    def _store_raw_annotation(self, workflow_id: str, annotation: str) -> None:
        # Straight into the database so this exercises the read-side
        # sanitization on its own, independent of any write path.
        sa_session = self._app.model.session
        stored_workflow = sa_session.get(StoredWorkflow, self._app.security.decode_id(workflow_id))
        assert stored_workflow is not None
        add_item_annotation(sa_session, stored_workflow.user, stored_workflow, annotation)
        sa_session.commit()

    def test_local_description_is_sanitized(self):
        index = self._curated_index(anon=True, limit=10)
        by_id = {workflow["id"]: workflow for workflow in index["workflows"]}
        description = by_id[self.published_ids[2]]["description"]
        assert "Safe text" in description
        assert "<script" not in description
        assert "onerror" not in description

    def test_local_search_with_many_keyed_terms_is_ok(self):
        # One SQL predicate per term used to overflow SQLite's expression tree.
        index = self._curated_index(anon=True, search=" ".join("name:x" for _ in range(1100)), limit=10)
        assert index["source"] == "local"

    def test_local_source_and_rows(self):
        index = self._curated_index(limit=10)
        assert index["source"] == "local"
        assert index["total_matches"] == 3
        assert len(index["workflows"]) == 3

        by_id = {workflow["id"]: workflow for workflow in index["workflows"]}
        assert set(by_id) == set(self.published_ids)
        for workflow in index["workflows"]:
            assert workflow["stored_workflow_id"] == workflow["id"]
            assert workflow["owner"] == CURATED_OWNER_USERNAME
            assert workflow["number_of_steps"]
            # These only exist for the IWC catalog; a local workflow carries none of them.
            assert workflow["external_url"] is None
            assert workflow["doi"] is None
            assert workflow["release"] is None
            assert workflow["trs_url"] is None
            assert workflow["trs_fallback_url"] is None
            assert workflow["collections"] == []

    def test_local_excludes_unpublished(self):
        index = self._curated_index(limit=10)
        ids = [workflow["id"] for workflow in index["workflows"]]
        assert self.unpublished_id not in ids

    def test_local_excludes_substring_username_owner(self):
        index = self._curated_index(limit=10)
        ids = [workflow["id"] for workflow in index["workflows"]]
        assert self.mirror_id not in ids
        owners = {workflow["owner"] for workflow in index["workflows"]}
        assert owners == {CURATED_OWNER_USERNAME}

    def test_local_search_name(self):
        index = self._curated_index(search="name:acurated", limit=10)
        assert index["total_matches"] == 1
        assert index["workflows"][0]["id"] == self.published_ids[0]

    def test_local_search_tag_exact_and_substring(self):
        exact = self._curated_index(search=f"tag:'curatedtag{self.token}'", limit=10)
        assert [workflow["id"] for workflow in exact["workflows"]] == [self.published_ids[0]]

        substring = self._curated_index(search=f"tag:curatedtag{self.token}", limit=10)
        assert {workflow["id"] for workflow in substring["workflows"]} == {
            self.published_ids[0],
            self.published_ids[1],
        }

    def test_local_pagination_is_consistent(self):
        first = self._curated_index(sort_by="name", sort_desc=False, limit=2, offset=0)
        second = self._curated_index(sort_by="name", sort_desc=False, limit=2, offset=2)

        assert first["total_matches"] == 3
        assert second["total_matches"] == first["total_matches"]
        assert len(first["workflows"]) == 2
        assert len(second["workflows"]) == 1

        paged = [workflow["id"] for workflow in first["workflows"] + second["workflows"]]
        assert len(set(paged)) == 3
        assert set(paged) == set(self.published_ids)
        names = [workflow["name"] for workflow in first["workflows"] + second["workflows"]]
        assert names == sorted(self.published_names)

    def test_local_is_exposed_to_the_client(self):
        assert self._get("configuration", anon=True).json()["curated_workflows_source"] == "local"

    def test_local_anonymous_access(self):
        # Discovery for logged-out newcomers is the point of the feature.
        index = self._curated_index(anon=True, limit=10)
        assert index["source"] == "local"
        assert index["total_matches"] == 3


class TestCuratedWorkflowsCatalog(_CuratedWorkflowsTestCase):
    """``curated_workflows_source: iwc``: the tab serves the on-disk IWC projection."""

    projection_path: ClassVar[str] = ""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.projection_path = os.path.join(cls._test_driver.mkdtemp(), "curated", "iwc_workflows.json")
        # Stand in for what the celery task writes, so the endpoint has a
        # catalog to serve without anything downloading one.
        curated.write_projection(cls.projection_path, CATALOG_ENTRIES)
        config["curated_workflows_source"] = "iwc"
        # Owners only count in local mode. Setting them here pins that they don't
        # quietly switch an iwc Galaxy over to listing local accounts.
        config["curated_workflow_owners"] = CURATED_OWNER_USERNAME
        config["curated_workflows_path"] = cls.projection_path

    def test_catalog_ignores_owners_outside_local_mode(self):
        assert self._get("configuration", anon=True).json()["curated_workflows_source"] == "iwc"
        index = self._curated_index(limit=10)
        assert index["source"] == "iwc"
        assert all(workflow["owner"] is None for workflow in index["workflows"])

    def test_catalog_source_and_rows(self):
        index = self._curated_index(limit=10)
        assert index["source"] == "iwc"
        assert index["total_matches"] == len(CATALOG_ENTRIES)
        assert [workflow["id"] for workflow in index["workflows"]] == CATALOG_IDS
        assert index["message"] is None

        for workflow in index["workflows"]:
            assert workflow["stored_workflow_id"] is None
            assert workflow["owner"] is None
            assert workflow["trs_url"].startswith(DOCKSTORE_TRS_TOOLS)
            assert workflow["trs_url"].endswith("/versions/v0.1")
            assert workflow["trs_fallback_url"].endswith("/versions/main")
            assert workflow["external_url"].startswith("https://iwc.galaxyproject.org/workflow/")

    def test_catalog_pagination_is_consistent(self):
        seen: list[str] = []
        for offset in (0, 2, 4):
            page = self._curated_index(limit=2, offset=offset)
            assert page["total_matches"] == len(CATALOG_ENTRIES)
            assert page["source"] == "iwc"
            seen.extend(workflow["id"] for workflow in page["workflows"])
        assert seen == CATALOG_IDS

    def test_catalog_search_name_and_tag(self):
        by_name = self._curated_index(search="name:assembly", limit=10)
        assert {workflow["id"] for workflow in by_name["workflows"]} == {"assembly-hifi", "assembly-flye"}
        assert by_name["total_matches"] == 2

        exact_tag = self._curated_index(search="tag:'assembly'", limit=10)
        assert exact_tag["total_matches"] == 2
        no_match = self._curated_index(search="tag:'assem'", limit=10)
        assert no_match["total_matches"] == 0
        assert no_match["workflows"] == []

    def test_catalog_anonymous_access(self):
        index = self._curated_index(anon=True, limit=10)
        assert index["source"] == "iwc"
        assert index["total_matches"] == len(CATALOG_ENTRIES)


class TestCuratedWorkflowsOff(_CuratedWorkflowsTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["curated_workflows_source"] = "off"

    def test_off_is_exposed_to_the_client(self):
        assert self._get("configuration", anon=True).json()["curated_workflows_source"] == "off"

    def test_off_returns_config_does_not_allow(self):
        response = self._curated_response()
        api_asserts.assert_status_code_is(response, 403)
        api_asserts.assert_error_code_is(response, error_codes.error_codes_by_name["CONFIG_DOES_NOT_ALLOW"])

    def test_off_anonymous_returns_config_does_not_allow(self):
        response = self._curated_response(anon=True)
        api_asserts.assert_status_code_is(response, 403)
        api_asserts.assert_error_code_is(response, error_codes.error_codes_by_name["CONFIG_DOES_NOT_ALLOW"])


class TestCuratedWorkflowsUnavailable(_CuratedWorkflowsTestCase):
    """No projection on disk and no way to fetch one -- the offline contract."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["curated_workflows_source"] = "iwc"
        config["curated_workflows_path"] = os.path.join(cls._test_driver.mkdtemp(), "missing", "iwc_workflows.json")

    def test_missing_projection_is_ok_not_server_error(self):
        response = self._curated_response(limit=10)
        # There is no 503 in galaxy.exceptions; the state travels in the body.
        api_asserts.assert_status_code_is(response, 200)
        index = response.json()
        assert index["source"] in ("preparing", "unavailable")
        assert index["workflows"] == []
        assert index["total_matches"] == 0
        assert index["message"]

    def test_anonymous_missing_projection_is_ok(self):
        response = self._curated_response(anon=True, limit=10)
        api_asserts.assert_status_code_is(response, 200)
        assert response.json()["source"] in ("preparing", "unavailable")

    def test_first_request_prepares_then_cooldown_reports_unavailable(self):
        # ``clear_caches`` zeroes the last-attempt stamp, but ``monotonic()`` is
        # time since boot on Linux and can itself be inside the cooldown window
        # on a freshly booted CI container. Push it provably past the window so
        # the first request is guaranteed to start a refresh.
        curated._last_refresh_attempt = monotonic() - curated.REFRESH_COOLDOWN_SECONDS - 1.0

        first = self._curated_index()
        assert first["source"] == "preparing"
        assert first["message"]

        self._wait_for_refresh_to_settle()
        self.refresh_mock.assert_called()

        # Within the cooldown the endpoint stops trying and says so, rather
        # than spawning a fetch per page view.
        second = self._curated_index()
        assert second["source"] == "unavailable"
        assert "iwc.galaxyproject.org" in second["message"]


class TestCuratedWorkflowsClientRoute(_CuratedWorkflowsTestCase):
    """The tab's URL has to be served by the SPA, not just exist in the Vue router."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["curated_workflows_source"] = "iwc"

    def test_curated_route_is_served_like_its_sibling_tabs(self):
        # Bookmarking or hard-refreshing the tab hits the server for this path.
        # Without an add_client_route registration it 404s while every other
        # workflow tab loads, which no API-level test would notice.
        for path in ("workflows/list_published", "workflows/list_curated"):
            response = requests.get(urljoin(self.url, path))
            api_asserts.assert_status_code_is(response, 200)
