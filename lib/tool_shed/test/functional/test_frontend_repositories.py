import re

from playwright.sync_api import expect

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

    def test_metadata_inspector_loads(self):
        """Verify Metadata Inspector page loads with repository data."""
        self._setup_repo_and_visit_inspector()
        page = self._page

        expect(page.locator("text=Metadata Inspector")).to_be_visible()
        # Always-visible tabs (Reset Metadata requires can_manage permission)
        expect(page.locator("[role=tab]").filter(has_text="Revisions")).to_be_visible()
        expect(page.locator("[role=tab]").filter(has_text="Tool History")).to_be_visible()
        expect(page.locator("[role=tab]").filter(has_text="Raw JSON")).to_be_visible()

    def test_metadata_inspector_default_tab(self):
        """Verify Revisions is the default landing tab."""
        repository = self._setup_repo_and_visit_inspector()
        page = self._page

        # Revisions tab active by default, repo name visible
        expect(page.locator("body")).to_contain_text(repository.name)

    def test_metadata_inspector_revisions_tab(self):
        """Verify Revisions tab shows changeset data."""
        self._setup_repo_and_visit_inspector()
        page = self._page

        page.locator("[role=tab]").filter(has_text="Revisions").click()
        # RevisionsTab renders a list of collapsible revisions showing changeset hashes
        expect(page.locator(".revision-list")).to_be_visible()

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

    def test_metadata_inspector_screenshots(self):
        """Capture screenshots of metadata inspector tabs."""
        self.login()
        self._setup_repo_and_visit_inspector(multi_revision=True)
        page = self._page

        # Revisions tab (default) - wait for content to load
        page.wait_for_selector("text=Metadata Inspector")
        page.wait_for_load_state("networkidle")
        self.screenshot("metadata_inspector_revisions")

        # Raw JSON tab
        page.locator("[role=tab]").filter(has_text="Raw JSON").click()
        page.wait_for_load_state("networkidle")
        self.screenshot("metadata_inspector_raw_json")

        # Tool History tab
        page.locator("[role=tab]").filter(has_text="Tool History").click()
        page.wait_for_load_state("networkidle")
        self.screenshot("metadata_inspector_tool_history")

        # Tool History with 1.3.0 details expanded
        page.locator(".tool-details-toggle").first.click()
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
        expect(page.locator(".reset-status-chip").filter(has_text="ok")).to_be_visible()

        self.screenshot("metadata_inspector_reset_complete")


class TestFrontendRepositoryContents(PlaywrightTestCase):
    """Anonymous browsing of repository files (no login in this class's browser)."""

    def _setup_column_maker(self):
        category = self.populator.new_category(prefix=TEST_CATEGORY_PREFIX)
        return self.populator.setup_test_data_repo("column_maker", category_id=category.id)

    def _revisions(self, repository) -> list[str]:
        metadata = self.populator.get_metadata(repository, downloadable_only=True)
        return [revision.changeset_revision for revision in metadata.root.values()]

    def test_contents_browse_and_view_file(self):
        repository = self._setup_column_maker()
        self.visit_url(f"/repositories/{repository.id}/contents")
        page = self._page

        expect(page.locator("h1")).to_have_text("Contents")
        folder = page.get_by_role("button", name="column_maker", exact=True)
        expect(folder).to_have_attribute("aria-expanded", "false")
        folder.click()
        expect(folder).to_have_attribute("aria-expanded", "true")

        # File paths keep real slashes in API requests and in the page URL
        with page.expect_response(lambda r: r.url.endswith("/files/column_maker/column_maker.xml")) as response:
            page.get_by_role("button", name="column_maker.xml").click()
        assert response.value.ok
        code = page.locator(".config-file-contents pre")
        expect(code).to_contain_text("<tool")
        # Defaults to the newest installable revision
        expect(code).to_contain_text('version="1.3.0"')
        expect(page).to_have_url(re.compile(r"\?file=column_maker/column_maker\.xml$"))
        expect(page.get_by_role("button", name="column_maker.xml")).to_have_attribute("aria-current", "true")
        self.screenshot("repository_contents_file")

    def test_contents_deep_link(self):
        repository = self._setup_column_maker()
        oldest = self._revisions(repository)[0]
        self.visit_url(f"/repositories/{repository.id}/contents?revision={oldest}&file=column_maker/column_maker.xml")
        page = self._page

        code = page.locator(".config-file-contents pre")
        expect(code).to_contain_text("<tool")
        expect(code).to_contain_text('version="1.1.0"')
        expect(page.get_by_role("button", name="column_maker", exact=True)).to_have_attribute("aria-expanded", "true")

    def test_explore_menu_links_contents(self):
        repository = self._setup_column_maker()
        newest = self._revisions(repository)[-1]
        self.visit_url(f"/repositories/{repository.id}")
        page = self._page

        page.get_by_role("button", name="Explore repository").click()
        # hgweb views are login-gated, so anonymous users get no changelog link
        expect(page.locator("a.dropdown-item").filter(has_text="Changelog")).to_have_count(0)
        page.locator("a.dropdown-item").filter(has_text="Contents").click()

        expect(page).to_have_url(re.compile(rf"/repositories/{repository.id}/contents\?revision={newest}$"))
        expect(page.get_by_role("button", name="column_maker", exact=True)).to_be_visible()
