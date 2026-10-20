import re

import yaml
from playwright.sync_api import expect

from galaxy_test.base.api_util import random_name
from tool_shed_client.schema import UpdateRepositoryRequest
from ..base.playwrightbrowser import Locators
from ..base.playwrighttestcase import PlaywrightTestCase
from ..base.populators import COLUMN_MAKER_PATH

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

    def test_old_revision_readme_renders_with_its_images(self):
        """Verify an old revision shows its README and that revision's image, even when the README is unchanged."""
        repository = self.populator.setup_test_data_repo("column_maker_with_rst_readme")
        revisions = list(self.populator.get_metadata(repository).root.values())
        assert len(revisions) == 3
        # The second revision only bumps the tool version, so README.rst and images/logo.png are unchanged in it.
        middle_changeset = revisions[1].changeset_revision
        self.visit_url(f"/view/{repository.owner}/{repository.name}/{middle_changeset}")
        page = self._page

        readme = page.locator(".repository-readme")
        expect(readme).to_contain_text("Old README for column maker.")
        expect(readme).not_to_contain_text("New README")
        # decode() rejects for a broken image; the old logo is 16px wide, the latest one 24px.
        assert readme.locator("img").evaluate("img => img.decode().then(() => img.naturalWidth)") == 16
        readme.scroll_into_view_if_needed()
        self.screenshot("repository_old_revision_readme")

        self.visit_url(f"/view/{repository.owner}/{repository.name}")
        expect(readme).to_contain_text("New README for column maker.")
        assert readme.locator("img").evaluate("img => img.decode().then(() => img.naturalWidth)") == 24
        readme.scroll_into_view_if_needed()
        self.screenshot("repository_latest_revision_readme")

    def test_repository_page_categories_clone_command_and_shed_yml(self):
        # Created out of alphabetical order, as the page lists them by name
        name_base = random_name(prefix=TEST_CATEGORY_PREFIX)
        beta = self.populator.new_category(name=f"{name_base} Beta")
        alpha = self.populator.new_category(name=f"{name_base} Alpha")
        repository = self.populator.new_repository([beta.id, alpha.id], prefix=TEST_REPO_PREFIX)
        assert self.populator.upload_revision(repository, COLUMN_MAKER_PATH).is_ok
        self.visit_url(f"/repositories/{repository.id}")
        page = self._page

        clone_url = f"{self.url.rstrip('/')}/repos/{repository.owner}/{repository.name}"
        clone_command = page.locator(Locators.repository_link_command)
        expect(clone_command).to_have_text(f"hg clone {clone_url}")
        categories = page.locator(Locators.repository_category)
        expect(categories).to_have_text([alpha.name, beta.name])
        shed_yml = (
            page.locator(Locators.config_file_contents)
            .filter(has=page.locator(Locators.config_file_contents_name, has_text=".shed.yml"))
            .locator(Locators.config_file_contents_body)
        )
        expect(shed_yml).to_contain_text(f"categories: - {alpha.name} - {beta.name}")
        # to_contain_text collapses whitespace, so check the YAML lines on the settled text
        shed_yml_text = shed_yml.inner_text()
        assert f"name: {repository.name}\nowner: {repository.owner}\n" in shed_yml_text
        assert f"categories:\n- {alpha.name}\n- {beta.name}" in shed_yml_text
        # The clone command ends the sticky aside; on this short page, scrolling to it shows all three
        clone_command.scroll_into_view_if_needed()
        self.screenshot("repository_categories_clone_command_and_shed_yml")

        categories.filter(has_text=beta.name).click()
        expect(page).to_have_url(re.compile(f"/repositories_by_category/{beta.id}$"))

    def test_repository_shed_yml_loads_back_with_pyyaml(self):
        # Planemo reads .shed.yml with PyYAML, so awkward values must load back unchanged
        category = self.populator.new_category(name=f"{random_name(prefix=TEST_CATEGORY_PREFIX)}: yes #1")
        synopsis = "Mapper: fast #1"
        homepage_url = "https://example.org/tool:"
        remote_repository_url = "https://github.com/galaxyproject/tools-iuc"
        # The first is written as a literal block, the second needs escapes
        for long_description in ["First line\nsecond: line #2\n\nthird\n", "First\r\nsecond\u2028third\n\n  indented"]:
            repository = self.populator.new_repository([category.id], prefix=TEST_REPO_PREFIX)
            self.populator.update(
                repository,
                UpdateRepositoryRequest(
                    synopsis=synopsis,
                    description=long_description,
                    homepage_url=homepage_url,
                    remote_repository_url=remote_repository_url,
                ),
            )
            self.visit_url(f"/repositories/{repository.id}")
            page = self._page

            shed_yml = (
                page.locator(Locators.config_file_contents)
                .filter(has=page.locator(Locators.config_file_contents_name, has_text=".shed.yml"))
                .locator(Locators.config_file_contents_body)
            )
            expect(shed_yml).to_contain_text(f"name: {repository.name}")
            assert yaml.safe_load(shed_yml.text_content()) == {
                "name": repository.name,
                "owner": repository.owner,
                "description": synopsis,
                "long_description": long_description,
                "homepage_url": homepage_url,
                "remote_repository_url": remote_repository_url,
                "type": "unrestricted",
                "categories": [category.name],
            }

    def test_repository_aside_end_reachable_on_long_page(self):
        repository = self.populator.setup_column_maker_repo(prefix=TEST_REPO_PREFIX)
        long_description = "A long description that runs well past the window. " * 600
        self.populator.update(repository, UpdateRepositoryRequest(description=long_description))
        self.visit_url(f"/repositories/{repository.id}")
        page = self._page

        clone_command = page.locator(Locators.repository_link_command)
        expect(clone_command).to_be_attached()
        # Halfway down, a sticky aside taller than the window must still show its last card
        page.evaluate("window.scrollTo(0, (document.body.scrollHeight - window.innerHeight) / 2)")
        expect(clone_command).to_be_in_viewport()
