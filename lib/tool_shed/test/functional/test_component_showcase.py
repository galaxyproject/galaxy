"""Playwright tests for component showcase screenshots.

Run with:
    TOOL_SHED_TEST_SCREENSHOTS=/tmp/component_screenshots TOOL_SHED_API_VERSION=v2 uv run pytest \
        tool_shed/test/functional/test_component_showcase.py -v

Screenshots are saved to TOOL_SHED_TEST_SCREENSHOTS directory if set.
"""

import os
import tempfile
from pathlib import Path

from playwright.sync_api import expect

from ..base.api import skip_if_api_v1
from ..base.playwrighttestcase import PlaywrightTestCase


class TestComponentShowcase(PlaywrightTestCase):
    """Screenshot tests for the component showcase page."""

    def _navigate_to_showcase(self):
        """Navigate to component showcase and wait for load."""
        self.visit_url("/_component_showcase")
        page = self._page
        page.wait_for_load_state("networkidle")
        expect(page.locator("text=This page is only meant for tool shed developers")).to_be_visible()

    def _screenshot_component(self, component_name: str) -> None:
        """Take screenshot of a component card including header and all examples."""
        page = self._page
        component = page.locator(".q-card").filter(has=page.locator(f".text-h6:has-text('{component_name}')"))
        expect(component).to_be_visible()
        screenshot_name = component_name.replace(" ", "_")
        component.screenshot(path=self._get_screenshot_path(screenshot_name))

    def _get_screenshot_path(self, name: str) -> str:
        """Get full path for screenshot, creating dir if needed."""
        screenshot_dir = os.environ.get("TOOL_SHED_TEST_SCREENSHOTS")
        if not screenshot_dir:
            screenshot_dir = tempfile.mkdtemp(prefix="component_showcase_")

        base_path = Path(screenshot_dir)
        base_path.mkdir(parents=True, exist_ok=True)
        return str(base_path / f"{name}.png")

    # === General Components ===

    @skip_if_api_v1
    def test_loading_div(self):
        """Screenshot LoadingDiv component."""
        self._navigate_to_showcase()
        self._screenshot_component("LoadingDiv")

    @skip_if_api_v1
    def test_error_banner(self):
        """Screenshot ErrorBanner component."""
        self._navigate_to_showcase()
        self._screenshot_component("ErrorBanner")

    @skip_if_api_v1
    def test_repository_link(self):
        """Screenshot RepositoryLink component."""
        self._navigate_to_showcase()
        self._screenshot_component("RepositoryLink")

    @skip_if_api_v1
    def test_repository_actions(self):
        """Screenshot RepositoryActions component."""
        self._navigate_to_showcase()
        self._screenshot_component("RepositoryActions")

    @skip_if_api_v1
    def test_recently_created_repositories(self):
        """Screenshot RecentlyCreatedRepositories component."""
        self._navigate_to_showcase()
        self._screenshot_component("RecentlyCreatedRepositories")

    @skip_if_api_v1
    def test_landing_search_box(self):
        """Screenshot LandingSearchBox component."""
        self._navigate_to_showcase()
        self._screenshot_component("LandingSearchBox")

    @skip_if_api_v1
    def test_landing_info_sections(self):
        """Screenshot LandingInfoSections component."""
        self._navigate_to_showcase()
        self._screenshot_component("LandingInfoSections")

    # === MetadataInspector Components ===

    @skip_if_api_v1
    def test_changeset_summary_table(self):
        """Screenshot ChangesetSummaryTable component."""
        self._navigate_to_showcase()
        self._screenshot_component("ChangesetSummaryTable")

    @skip_if_api_v1
    def test_json_diff_viewer(self):
        """Screenshot JsonDiffViewer component."""
        self._navigate_to_showcase()
        self._screenshot_component("JsonDiffViewer")

    @skip_if_api_v1
    def test_metadata_json_viewer(self):
        """Screenshot MetadataJsonViewer component."""
        self._navigate_to_showcase()
        self._screenshot_component("MetadataJsonViewer")

    @skip_if_api_v1
    def test_revisions_tab(self):
        """Screenshot RevisionsTab component."""
        self._navigate_to_showcase()
        self._screenshot_component("RevisionsTab")

    @skip_if_api_v1
    def test_overview_tab(self):
        """Screenshot OverviewTab component."""
        self._navigate_to_showcase()
        self._screenshot_component("OverviewTab")

    @skip_if_api_v1
    def test_tool_history_tab(self):
        """Screenshot ToolHistoryTab component."""
        self._navigate_to_showcase()
        self._screenshot_component("ToolHistoryTab")
