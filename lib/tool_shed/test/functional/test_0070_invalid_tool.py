from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

repository_name = "bismark_0070"
repository_description = "Galaxy's bismark wrapper"
repository_long_description = "Long description of Galaxy's bismark wrapper"
category_name = "Test 0070 Invalid Tool Revisions"
category_description = "Tests for a repository with invalid tool revisions."


class TestBismarkRepository(ShedTwillTestCase):
    """Testing bismark with valid and invalid tool entries."""

    def test_0000_create_or_login_admin_user(self):
        """Create necessary user accounts and login as an admin user."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_category_and_repository(self):
        """Create a category for this test suite, then create and populate a bismark repository. It should contain at least one each valid and invalid tool."""
        category = self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name=repository_name,
            description=repository_description,
            long_description=repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        self.user_populator().setup_bismark_repo(repository)
        invalid_revision = self.get_repository_first_revision(repository)
        self.display_manage_repository_page(repository, strings_displayed=[self.invalid_tools_labels])
        valid_revision = self.get_repository_tip(repository)
        tool_guid = f"{self.url.replace('http://', '').rstrip('/')}/repos/user1/bismark_0070/bismark_methylation_extractor/0.7.7.3"
        tool_metadata_strings_displayed = [
            tool_guid,
            "0.7.7.3",  # The tool version.
            "bismark_methylation_extractor",  # The tool ID.
            "Bismark",  # The tool name.
            "methylation extractor",
        ]  # The tool description.
        tool_page_strings_displayed = ["Bismark (version 0.7.7.3)"]
        self.check_repository_tools_for_changeset_revision(
            repository,
            valid_revision,
            tool_metadata_strings_displayed=tool_metadata_strings_displayed,
            tool_page_strings_displayed=tool_page_strings_displayed,
        )
        self.check_repository_invalid_tools_for_changeset_revision(repository, invalid_revision)
