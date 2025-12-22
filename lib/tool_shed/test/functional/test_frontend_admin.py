"""Playwright tests for admin-only functionality.

Run with:
    TOOL_SHED_API_VERSION=v2 uv run pytest \
        tool_shed/test/functional/test_frontend_admin.py -v
"""

from playwright.sync_api import expect

from ..base.api import skip_if_api_v1
from ..base.playwrighttestcase import PlaywrightTestCase

TEST_CATEGORY_PREFIX = "admintestcategory"
TEST_REPO_PREFIX = "admintestcolumnmaker"


class TestFrontendAdmin(PlaywrightTestCase):
    """Frontend tests for admin-only pages and functionality."""

    @skip_if_api_v1
    def test_admin_page_loads_when_logged_in(self):
        """Verify admin page loads for admin user."""
        self.login()
        self.visit_url("/admin")
        page = self._page
        page.wait_for_load_state("networkidle")

        # Admin page should show re-index button
        expect(page.get_by_role("button", name="Re-index search")).to_be_visible()

    @skip_if_api_v1
    def test_reindex_search(self):
        """Verify Re-index search button works and returns results."""
        self.login()

        # Create a repo so we have something to index
        category = self.populator.new_category(prefix=TEST_CATEGORY_PREFIX)
        self.populator.setup_column_maker_repo(
            prefix=TEST_REPO_PREFIX,
            category_id=category.id,
        )

        # Navigate to admin page
        self.visit_url("/admin")
        page = self._page
        page.wait_for_load_state("networkidle")

        # Click re-index button
        page.get_by_role("button", name="Re-index search").click()

        # Wait for results to appear (contains indexed counts)
        expect(page.locator("text=repositories_indexed")).to_be_visible(timeout=30000)
        expect(page.locator("text=tools_indexed")).to_be_visible()

    @skip_if_api_v1
    def test_admin_page_screenshot(self):
        """Capture screenshot of admin page with re-index results."""
        self.login()

        # Create a repo for indexing
        category = self.populator.new_category(prefix=TEST_CATEGORY_PREFIX)
        self.populator.setup_column_maker_repo(
            prefix=TEST_REPO_PREFIX,
            category_id=category.id,
        )

        self.visit_url("/admin")
        page = self._page
        page.wait_for_load_state("networkidle")

        # Take screenshot before clicking
        self.screenshot("admin_page")

        # Click re-index and capture result
        page.get_by_role("button", name="Re-index search").click()
        expect(page.locator("text=repositories_indexed")).to_be_visible(timeout=30000)

        self.screenshot("admin_page_reindex_results")
