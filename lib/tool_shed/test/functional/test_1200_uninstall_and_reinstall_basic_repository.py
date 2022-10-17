from ..base.twilltestcase import (
    common,
    ShedTwillTestCase,
)


class TestUninstallingAndReinstallingRepositories(ShedTwillTestCase):
    """Test uninstalling and reinstalling a basic repository."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)
        self.galaxy_login(email=common.admin_email, username=common.admin_username)

    def test_0005_ensure_repositories_and_categories_exist(self):
        """Create the 0000 category and upload the filtering repository to the tool shed, if necessary."""
        category = self.create_category(
            name="Test 0000 Basic Repository Features 1", description="Test 0000 Basic Repository Features 1"
        )
        self.create_category(
            name="Test 0000 Basic Repository Features 2", description="Test 0000 Basic Repository Features 2"
        )
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name="filtering_0000",
            description="Galaxy's filtering tool for test 0000",
            long_description="Long description of Galaxy's filtering tool for test 0000",
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

    def test_0010_install_filtering_repository(self):
        """Install the filtering repository into the Galaxy instance."""
        self.galaxy_login(email=common.admin_email, username=common.admin_username)
        self._install_repository(
            "filtering_0000",
            common.test_user_1_name,
            "Test 0000 Basic Repository Features 1",
            new_tool_panel_section_label="test_1000",
        )
        self._assert_has_installed_repos_with_names("filtering_0000")

    def test_0015_uninstall_filtering_repository(self):
        """Uninstall the filtering repository."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            "filtering_0000", common.test_user_1_name
        )
        self.uninstall_repository(installed_repository)
        self._assert_has_no_installed_repos_with_names("filtering_0000")

    def test_0020_reinstall_filtering_repository(self):
        """Reinstall the filtering repository."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            "filtering_0000", common.test_user_1_name
        )
        self.reinstall_repository_api(installed_repository)
        self._assert_has_installed_repos_with_names("filtering_0000")
        self._assert_has_valid_tool_with_name("Filter1")
        self._assert_repo_has_tool_with_id(installed_repository, "Filter1")

    def test_0025_deactivate_filtering_repository(self):
        """Deactivate the filtering repository without removing it from disk."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            "filtering_0000", common.test_user_1_name
        )
        self.deactivate_repository(installed_repository)
        self._assert_has_no_installed_repos_with_names("filtering_0000")

    def test_0030_reactivate_filtering_repository(self):
        """Reactivate the filtering repository and verify that it now shows up in the list of installed repositories."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            "filtering_0000", common.test_user_1_name
        )
        self.reactivate_repository(installed_repository)
        self._assert_has_installed_repos_with_names("filtering_0000")
        self._assert_has_valid_tool_with_name("Filter1")
        self._assert_repo_has_tool_with_id(installed_repository, "Filter1")
