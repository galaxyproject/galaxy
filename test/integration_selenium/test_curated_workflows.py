"""Browser tests for the curated workflows tab under each catalog source.

Offline like the API tests in ``test/integration/test_curated_workflows.py``:
``CuratedWorkflowsNetworkGuard`` fails any attempt to fetch the real IWC
catalog, and the IWC case serves that module's catalog fixture from disk.
"""

import json
import os
import shutil
from typing import (
    Any,
    ClassVar,
)
from uuid import uuid4

from galaxy.selenium.smart_components import SmartTarget
from galaxy_test.base.populators import WorkflowPopulator
from galaxy_test.driver.integration_setup import (
    CuratedWorkflowsNetworkGuard,
    store_raw_annotation,
)
from galaxy_test.selenium.framework import retry_assertion_during_transitions
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)

IWC_CATALOG_FIXTURE = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__), os.pardir, "integration", "curated_workflows", "iwc_catalog", "iwc_workflows.json"
    )
)
with open(IWC_CATALOG_FIXTURE) as fixture:
    CATALOG_ENTRIES: list[dict[str, Any]] = json.load(fixture)["workflows"]

CATALOG_NAMES = {entry["name"] for entry in CATALOG_ENTRIES}
ASSEMBLY_COLLECTION = "Genome assembly"
ASSEMBLY_NAMES = {entry["name"] for entry in CATALOG_ENTRIES if ASSEMBLY_COLLECTION in entry["collections"]}
# Only the Flye entry mentions flye in any searched field.
FLYE_NAMES = {entry["name"] for entry in CATALOG_ENTRIES if "flye" in entry["name"].lower()}

# See test/integration/test_curated_workflows.py for how the username is derived.
CURATED_OWNER_EMAIL = "curatedseleniumowner@bx.psu.edu"
CURATED_OWNER_USERNAME = "curatedseleniumowner--bx--psu--edu"


class _CuratedWorkflowsSeleniumTestCase(CuratedWorkflowsNetworkGuard, SeleniumIntegrationTestCase):
    ensure_registered = True

    @retry_assertion_during_transitions
    def _assert_curated_titles(self, expected: set[str]) -> None:
        titles = self.curated_workflow_card_titles()
        assert set(titles) == expected, titles

    def _open_advanced_search(self) -> None:
        self.components.workflows.advanced_search_toggle.wait_for_and_click()
        self.components.workflows.curated_advanced_search_name_input.wait_for_visible()

    def _run_advanced_search(self, field: SmartTarget, value: str) -> None:
        """Fill one field of the advanced menu and run the search.

        The curated tab uses FilterMenu's compact view, which renders no apply
        button; each field submits the whole menu on enter instead.
        """
        field.wait_for_and_send_keys(value)
        field.wait_for_and_send_enter()


class TestCuratedWorkflowsIwcSelenium(_CuratedWorkflowsSeleniumTestCase):
    """``curated_workflows_source: iwc``: the tab lists the catalog fixture."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        # Served from a copy so the projection's mtime is fresh and Galaxy can't write into the source tree.
        projection_path = os.path.join(cls._test_driver.mkdtemp(), "iwc_workflows.json")
        shutil.copyfile(IWC_CATALOG_FIXTURE, projection_path)
        config["curated_workflows_source"] = "iwc"
        config["curated_workflows_path"] = projection_path

    @selenium_test
    def test_catalog_lists_fixture(self):
        self.navigate_to_curated_workflows()
        self._assert_curated_titles(CATALOG_NAMES)
        self.screenshot("curated_workflows_iwc_index")

    @selenium_test
    def test_free_text_search(self):
        self.navigate_to_curated_workflows()
        self._assert_curated_titles(CATALOG_NAMES)
        self.workflow_index_search_for("flye")
        self._assert_curated_titles(FLYE_NAMES)

        self.workflow_index_search_for("nosuchcuratedworkflow")
        self.components.workflows.curated_workflow_not_found_message.wait_for_visible()

    @selenium_test
    def test_collection_chip_filters(self):
        self.navigate_to_curated_workflows()
        self.components.workflows.curated_collection_chip(name=ASSEMBLY_COLLECTION).wait_for_and_click()
        self._assert_curated_titles(ASSEMBLY_NAMES)
        assert self.workflow_index_get_current_filter() == f"collection:'{ASSEMBLY_COLLECTION}'"
        self.screenshot("curated_workflows_iwc_collection")

        # Clicking the active chip again clears it.
        self.components.workflows.curated_collection_chip(name=ASSEMBLY_COLLECTION).wait_for_and_click()
        self._assert_curated_titles(CATALOG_NAMES)
        assert self.workflow_index_get_current_filter() == ""

    @selenium_test
    def test_advanced_search_collection(self):
        self.navigate_to_curated_workflows()
        self._open_advanced_search()
        self.screenshot("curated_workflows_iwc_advanced_search")
        self._run_advanced_search(
            self.components.workflows.curated_advanced_search_collection_input, ASSEMBLY_COLLECTION
        )
        self._assert_curated_titles(ASSEMBLY_NAMES)
        # Unquoted: the curated filters are built with `quoteStrings` off, so a value
        # runs to the next `key:` token. The chips write the quoted form instead; both
        # reach the same workflows, which is what the assertion above covers.
        assert self.workflow_index_get_current_filter() == f"collection:{ASSEMBLY_COLLECTION}"


class TestCuratedWorkflowsLocalSelenium(_CuratedWorkflowsSeleniumTestCase):
    """``curated_workflows_source: local``: the tab lists the owners' published workflows."""

    published_names: ClassVar[list[str]] = []
    unpublished_name: ClassVar[str] = ""
    annotation_term: ClassVar[str] = ""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["curated_workflows_source"] = "local"
        config["curated_workflow_owners"] = CURATED_OWNER_USERNAME

    def setUp(self):
        super().setUp()
        if not TestCuratedWorkflowsLocalSelenium.published_names:
            self._create_fixtures()

    def _create_fixtures(self) -> None:
        fixtures = TestCuratedWorkflowsLocalSelenium
        token = uuid4().hex
        owner, _ = self._setup_user_get_key(CURATED_OWNER_EMAIL)
        owner_detail = self._get(f"users/{owner['id']}", admin=True).json()
        assert owner_detail["username"] == CURATED_OWNER_USERNAME, owner_detail["username"]

        owner_workflows = WorkflowPopulator(self.galaxy_interactor)
        fixtures.published_names = [f"curated {prefix} {token}" for prefix in ("alpha", "beta")]
        fixtures.unpublished_name = f"curated hidden {token}"
        with self._different_user(CURATED_OWNER_EMAIL):
            published_ids = [owner_workflows.simple_workflow(name, publish=True) for name in fixtures.published_names]
            owner_workflows.simple_workflow(fixtures.unpublished_name)

        # A term found only in the first workflow's annotation, never in a name or tag.
        fixtures.annotation_term = f"annotationonly{token}"
        store_raw_annotation(self._app, published_ids[0], f"Describes {fixtures.annotation_term} data")

    @selenium_test
    def test_lists_owner_published_workflows(self):
        self.navigate_to_curated_workflows()
        self._assert_curated_titles(set(self.published_names))
        self.screenshot("curated_workflows_local_index")

    @selenium_test
    def test_free_text_search_matches_owner_annotation(self):
        self.navigate_to_curated_workflows()
        self._assert_curated_titles(set(self.published_names))
        self.workflow_index_search_for(self.annotation_term)
        self._assert_curated_titles({self.published_names[0]})

    @selenium_test
    def test_advanced_search_omits_collection(self):
        self.navigate_to_curated_workflows()
        self._open_advanced_search()
        self.components.workflows.curated_advanced_search_collection_input.assert_absent()
        self.screenshot("curated_workflows_local_advanced_search")
