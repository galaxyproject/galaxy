from playwright.sync_api import expect

from ..base.api import skip_if_api_v1
from ..base.playwrighttestcase import PlaywrightTestCase

TEST_CATEGORY_PREFIX = "guitestcategory"
TEST_REPO_PREFIX = "guitestcolumnmaker"


class TestFrontendRepositories(PlaywrightTestCase):
    """Frontend tests for repository pages including Metadata Inspector."""

    def _setup_repo_and_visit_inspector(self, multi_revision=False):
        """Create test repo and navigate to metadata inspector.

        Args:
            multi_revision: If True, use column_maker test data with 3 revisions.
                           If False, use single revision for faster tests.
        """
        category = self.populator.new_category(prefix=TEST_CATEGORY_PREFIX)
        if multi_revision:
            repository = self.populator.setup_test_data_repo(
                "column_maker",
                category_id=category.id,
            )
        else:
            repository = self.populator.setup_column_maker_repo(
                prefix=TEST_REPO_PREFIX,
                category_id=category.id,
            )
        self.visit_url(f"/repositories/{repository.id}/metadata-inspector")
        return repository

    @skip_if_api_v1
    def test_metadata_inspector_loads(self):
        """Verify Metadata Inspector page loads with repository data."""
        self._setup_repo_and_visit_inspector()
        page = self._page

        expect(page.locator("text=Metadata Inspector")).to_be_visible()
        # Always-visible tabs (Reset Metadata requires can_manage permission)
        expect(page.locator("[role=tab]").filter(has_text="Overview")).to_be_visible()
        expect(page.locator("[role=tab]").filter(has_text="Revisions")).to_be_visible()
        expect(page.locator("[role=tab]").filter(has_text="Tool History")).to_be_visible()

    @skip_if_api_v1
    def test_metadata_inspector_overview_tab(self):
        """Verify Overview tab shows repository info."""
        repository = self._setup_repo_and_visit_inspector()
        page = self._page

        # Overview tab active by default, repo name visible
        expect(page.locator("body")).to_contain_text(repository.name)

    @skip_if_api_v1
    def test_metadata_inspector_revisions_tab(self):
        """Verify Revisions tab shows changeset data."""
        self._setup_repo_and_visit_inspector()
        page = self._page

        page.locator("[role=tab]").filter(has_text="Revisions").click()
        # RevisionsTab uses q-list with expansion items showing changeset hashes
        expect(page.locator(".q-list")).to_be_visible()

    @skip_if_api_v1
    def test_metadata_inspector_reset_tab(self):
        """Verify Reset Metadata tab with admin login."""
        self.login()
        self._setup_repo_and_visit_inspector()
        page = self._page

        # Reset tab should be visible when logged in as admin
        reset_tab = page.locator("[role=tab]").filter(has_text="Reset Metadata")
        expect(reset_tab).to_be_visible()
        reset_tab.click()

        # Preview button should be visible
        expect(page.get_by_role("button", name="Preview")).to_be_visible()

    @skip_if_api_v1
    def test_metadata_inspector_screenshots(self):
        """Capture screenshots of metadata inspector tabs."""
        self.login()
        self._setup_repo_and_visit_inspector(multi_revision=True)
        page = self._page

        # Overview tab (default) - wait for content to load
        page.wait_for_selector("text=Metadata Inspector")
        page.wait_for_load_state("networkidle")
        self.screenshot("metadata_inspector_overview")

        # Revisions tab
        page.locator("[role=tab]").filter(has_text="Revisions").click()
        page.wait_for_load_state("networkidle")
        self.screenshot("metadata_inspector_revisions")

        # Tool History tab
        page.locator("[role=tab]").filter(has_text="Tool History").click()
        page.wait_for_load_state("networkidle")
        self.screenshot("metadata_inspector_tool_history")

        # Tool History with 1.3.0 details expanded
        page.locator(".q-expansion-item").first.click()
        page.wait_for_timeout(500)  # Wait for expansion animation
        self.screenshot("metadata_inspector_tool_history_expanded")

        # Reset Metadata tab
        page.locator("[role=tab]").filter(has_text="Reset Metadata").click()
        page.wait_for_load_state("networkidle")
        self.screenshot("metadata_inspector_reset")

        # Reset Metadata after clicking Preview Changes
        page.get_by_role("button", name="Preview Changes").click()
        page.wait_for_selector("text=Preview Results")  # Wait for results
        self.screenshot("metadata_inspector_reset_preview")

    @skip_if_api_v1
    def test_metadata_inspector_reset_full(self):
        """Perform a full metadata reset and verify completion."""
        self.login()
        self._setup_repo_and_visit_inspector(multi_revision=True)
        page = self._page

        # Navigate to Reset Metadata tab
        page.locator("[role=tab]").filter(has_text="Reset Metadata").click()
        page.wait_for_load_state("networkidle")

        # Preview changes first
        page.get_by_role("button", name="Preview Changes").click()
        page.wait_for_selector("text=Preview Results")
        expect(page.locator("text=(dry run)")).to_be_visible()

        # Apply the reset
        page.get_by_role("button", name="Apply Now").click()
        page.wait_for_selector("text=Reset Complete", timeout=60000)

        # Verify dry run indicator is gone and status shows success
        expect(page.locator("text=(dry run)")).not_to_be_visible()
        expect(page.locator(".q-chip").filter(has_text="ok")).to_be_visible()

        self.screenshot("metadata_inspector_reset_complete")
