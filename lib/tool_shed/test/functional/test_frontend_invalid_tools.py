from playwright.sync_api import expect

from ..base.playwrighttestcase import PlaywrightTestCase


class TestFrontendInvalidTools(PlaywrightTestCase):
    """Test that the Tool Shed frontend displays invalid tool error messages."""

    def test_invalid_tools_display_error_message(self):
        """Navigate to a repository with invalid tools and verify the error reason is shown."""
        populator = self.populator
        repository = populator.setup_bismark_repo()
        repository_metadata = populator.get_metadata(repository)
        assert repository_metadata

        # Verify the API returns error messages
        revision = repository_metadata.latest_revision
        assert revision.invalid_tools
        invalid_tool = revision.invalid_tools[0]
        assert invalid_tool.tool_config
        assert invalid_tool.error_message

        # Navigate to the repository page in the frontend
        assert not isinstance(repository, str)
        page = self._page
        page.goto(f"{self.url}/repositories/{repository.id}")

        # Wait for the page to load and the Invalid Tools section to appear
        invalid_tools_header = page.locator("text=Invalid Tools")
        expect(invalid_tools_header).to_be_visible(timeout=10000)

        # Verify the tool config filename is displayed
        expect(page.locator("body")).to_contain_text(invalid_tool.tool_config)

        # Verify the error message is displayed (bismark tools reference missing .loc files)
        expect(page.locator("body")).to_contain_text(invalid_tool.error_message)
