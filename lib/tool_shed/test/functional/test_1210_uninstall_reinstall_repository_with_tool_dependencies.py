import os

from ..base.twilltestcase import (
    common,
    ShedTwillTestCase,
)


class TestUninstallingAndReinstallingRepositories(ShedTwillTestCase):
    """Test uninstalling and reinstalling a repository with tool dependencies."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.galaxy_login(email=common.admin_email, username=common.admin_username)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_ensure_repositories_and_categories_exist(self):
        """Create the 0010 category and upload the freebayes repository to the tool shed, if necessary."""
        category = self.create_category(
            name="Test 0010 Repository With Tool Dependencies",
            description="Tests for a repository with tool dependencies.",
        )
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name="freebayes_0010",
            description="Galaxy's freebayes tool",
            long_description="Long description of Galaxy's freebayes tool",
            owner=common.test_user_1_name,
            category=category,
        )
        if self.repository_is_new(repository):
            self.upload_file(
                repository,
                filename="freebayes/freebayes.xml",
                filepath=None,
                valid_tools_only=False,
                uncompress_file=False,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded the tool xml.",
                strings_displayed=[
                    "Metadata may have been defined",
                    "This file requires an entry",
                    "tool_data_table_conf",
                ],
                strings_not_displayed=[],
            )
            self.upload_file(
                repository,
                filename="freebayes/tool_data_table_conf.xml.sample",
                filepath=None,
                valid_tools_only=False,
                uncompress_file=False,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded the tool data table sample file.",
                strings_displayed=[],
                strings_not_displayed=[],
            )
            self.upload_file(
                repository,
                filename="freebayes/sam_fa_indices.loc.sample",
                filepath=None,
                valid_tools_only=True,
                uncompress_file=False,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded tool data table .loc file.",
                strings_displayed=[],
                strings_not_displayed=[],
            )
            self.upload_file(
                repository,
                filename=os.path.join("freebayes", "malformed_tool_dependencies", "tool_dependencies.xml"),
                filepath=None,
                valid_tools_only=False,
                uncompress_file=False,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded malformed tool dependency XML.",
                strings_displayed=["Exception attempting to parse", "invalid element name"],
                strings_not_displayed=[],
            )
            self.upload_file(
                repository,
                filename=os.path.join("freebayes", "invalid_tool_dependencies", "tool_dependencies.xml"),
                filepath=None,
                valid_tools_only=False,
                uncompress_file=False,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded invalid tool dependency XML.",
                strings_displayed=[
                    "The settings for <b>name</b>, <b>version</b> and <b>type</b> from a contained tool configuration"
                ],
                strings_not_displayed=[],
            )
            self.upload_file(
                repository,
                filename=os.path.join("freebayes", "tool_dependencies.xml"),
                filepath=None,
                valid_tools_only=True,
                uncompress_file=False,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded valid tool dependency XML.",
                strings_displayed=[],
                strings_not_displayed=[],
            )

    def test_0010_install_freebayes_repository(self):
        """Install the freebayes repository into the Galaxy instance."""
        self.galaxy_login(email=common.admin_email, username=common.admin_username)
        self._install_repository(
            "freebayes_0010",
            common.test_user_1_name,
            "Test 0010 Repository With Tool Dependencies",
            new_tool_panel_section_label="test_1210",
        )
        self._assert_has_installed_repos_with_names("freebayes_0010")

    def test_0015_uninstall_freebayes_repository(self):
        """Uninstall the freebayes repository."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            "freebayes_0010", common.test_user_1_name
        )
        self.uninstall_repository(installed_repository)
        self._assert_has_no_installed_repos_with_names("freebayes_0010")

    def test_0020_reinstall_freebayes_repository(self):
        """Reinstall the freebayes repository."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            "freebayes_0010", common.test_user_1_name
        )
        self.reinstall_repository_api(installed_repository)
        self._assert_has_installed_repos_with_names("freebayes_0010")
        self._assert_has_valid_tool_with_name("FreeBayes")
        self._assert_repo_has_tool_with_id(installed_repository, "freebayes")

    def test_0025_deactivate_freebayes_repository(self):
        """Deactivate the freebayes repository without removing it from disk."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            "freebayes_0010", common.test_user_1_name
        )
        self.deactivate_repository(installed_repository)
        self._assert_has_no_installed_repos_with_names("freebayes_0010")

    def test_0030_reactivate_freebayes_repository(self):
        """Reactivate the freebayes repository and verify that it now shows up in the list of installed repositories."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            "freebayes_0010", common.test_user_1_name
        )
        self.reactivate_repository(installed_repository)
        self._assert_has_installed_repos_with_names("freebayes_0010")
        self._assert_has_valid_tool_with_name("FreeBayes")
        self._assert_repo_has_tool_with_id(installed_repository, "freebayes")
