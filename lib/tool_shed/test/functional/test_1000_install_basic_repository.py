from ..base.twilltestcase import (
    common,
    ShedTwillTestCase,
)

repo_name = "filtering_0000"
repo_description = "Galaxy's filtering tool"


class TestBasicToolShedFeatures(ShedTwillTestCase):
    """Test installing a basic repository."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)
        self.galaxy_login(email=common.admin_email, username=common.admin_username)

    def test_0005_ensure_repositories_and_categories_exist(self):
        """Create the 0000 category and upload the filtering repository to it, if necessary."""
        self.login(email=common.admin_email, username=common.admin_username)
        category = self.create_category(
            name="Test 0000 Basic Repository Features 2",
            description="Test Description 0000 Basic Repository Features 2",
        )
        category = self.create_category(
            name="Test 0000 Basic Repository Features 1",
            description="Test Description 0000 Basic Repository Features 1",
        )
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name=repo_name,
            description=repo_description,
            long_description="Long description of Galaxy's filtering tool",
            owner=common.test_user_1_name,
            category=category,
        )
        if self.repository_is_new(repository):
            self.upload_file(
                repository,
                filename="filtering/filtering_1.1.0.tar",
                filepath=None,
                valid_tools_only=True,
                uncompress_file=True,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded filtering 1.1.0 tarball.",
                strings_displayed=[],
                strings_not_displayed=[],
            )
            self.upload_file(
                repository,
                filename="filtering/filtering_0000.txt",
                filepath=None,
                valid_tools_only=True,
                uncompress_file=False,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded readme for 1.1.0",
                strings_displayed=[],
                strings_not_displayed=[],
            )
            self.upload_file(
                repository,
                filename="filtering/filtering_2.2.0.tar",
                filepath=None,
                valid_tools_only=True,
                uncompress_file=True,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded filtering 2.2.0 tarball.",
                strings_displayed=[],
                strings_not_displayed=[],
            )
            self.upload_file(
                repository,
                filename="readme.txt",
                filepath=None,
                valid_tools_only=True,
                uncompress_file=False,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded readme for 2.2.0",
                strings_displayed=[],
                strings_not_displayed=[],
            )

    def test_0010_browse_tool_sheds(self):
        """Browse the available tool sheds in this Galaxy instance."""
        self.galaxy_login(email=common.admin_email, username=common.admin_username)
        self.browse_tool_shed(
            url=self.url,
            strings_displayed=["Test 0000 Basic Repository Features 1", "Test 0000 Basic Repository Features 2"],
        )

    def test_0015_browse_test_0000_category(self):
        """Browse the category created in test 0000. It should contain the filtering_0000 repository also created in that test."""
        category = self.populator.get_category_with_name("Test 0000 Basic Repository Features 1")
        self.browse_category(category, strings_displayed=[repo_name])

    def test_0020_preview_filtering_repository(self):
        """Load the preview page for the filtering_0000 repository in the tool shed."""
        self.preview_repository_in_tool_shed(
            repo_name, common.test_user_1_name, strings_displayed=[repo_name, "Valid tools"]
        )

    def test_0025_install_filtering_repository(self):
        self._install_repository(
            repo_name,
            common.test_user_1_name,
            "Test 0000 Basic Repository Features 1",
            new_tool_panel_section_label="test_1000",
        )
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            repo_name, common.test_user_1_name
        )
        changeset = str(installed_repository.installed_changeset_revision)
        assert self.get_installed_repository_for(common.test_user_1, repo_name, changeset)
        self._assert_has_valid_tool_with_name("Filter1")
        self._assert_repo_has_tool_with_id(installed_repository, "Filter1")

    def test_0030_install_filtering_repository_again(self):
        """Attempt to install the already installed filtering repository."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            repo_name, common.test_user_1_name
        )
        # Just make sure the repo is still installed, used to monitoring tests but we've
        # removed that page.
        self._install_repository(
            repo_name,
            common.test_user_1_name,
            "Test 0000 Basic Repository Features 1",
        )
        changeset = str(installed_repository.installed_changeset_revision)
        assert self.get_installed_repository_for(common.test_user_1, repo_name, changeset)

    def test_0035_verify_installed_repository_metadata(self):
        """Verify that resetting the metadata on an installed repository does not change the metadata."""
        self.verify_installed_repository_metadata_unchanged(repo_name, common.test_user_1_name)
