import logging

from ..base.twilltestcase import (
    common,
    ShedTwillTestCase,
)

log = logging.getLogger(__name__)

category_name = "Test 1460 Data Manager"
category_description = "Test script 1460 for testing Data Managers"
data_manager_repository_name = "data_manager_1460"
data_manager_repository_description = "Repository that contains a Data Manager"
data_manager_repository_long_description = f"{data_manager_repository_name}: {data_manager_repository_description}"
data_manager_name = "testing_data_manager"
data_manager_tar_file = "1460_files/data_manager_files/test_data_manager.tar"

"""
1. Add a Data Manager to toolshed

2. install Data Manager

3. Check that Data Manager tool

"""

# TODO: Allow testing actual Execution of installed Data Manager Tool.


class TestDataManagers(ShedTwillTestCase):
    """Test installing a repository containing a Data Manager."""

    def test_0000_initiate_users_and_category(self):
        """Create necessary user accounts and login as an admin user."""
        self.login(email=common.admin_email, username=common.admin_username)
        self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_2_email, username=common.test_user_2_name)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)

    def test_0010_create_data_manager_repository(self):
        """Create and populate data_manager_1460.

        This is step 1 - Create repository data_manager_1460.

        Create and populate a repository that contains a Data manager.
        """
        category = self.populator.get_category_with_name(category_name)
        repository = self.get_or_create_repository(
            name=data_manager_repository_name,
            description=data_manager_repository_description,
            long_description=data_manager_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        # Upload the data manager files to the repository.
        self.upload_file(
            repository,
            filename=data_manager_tar_file,
            filepath=None,
            valid_tools_only=True,
            uncompress_file=True,
            remove_repo_files_not_in_tar=False,
            commit_message=f"Populate {data_manager_repository_name} with a data manager configuration.",
            strings_displayed=[],
            strings_not_displayed=[],
        )

    def test_0020_install_data_manager_repository(self):
        """Install the data_manager_1460 repository to galaxy.

        This is step 3 - Attempt to install the repository into a galaxy instance, verify that it is installed.
        """
        self.galaxy_login(email=common.admin_email, username=common.admin_username)
        self._install_repository(
            data_manager_repository_name,
            common.test_user_1_name,
            category_name,
            install_tool_dependencies=True,
        )

    def test_0030_verify_data_manager_tool(self):
        """Verify that the data_manager_1460 repository is installed and Data Manager tool appears in list in Galaxy."""
        repository = self.test_db_util.get_installed_repository_by_name_owner(
            data_manager_repository_name, common.test_user_1_name
        )
        strings_displayed = ["status", "jobs", data_manager_name]
        self.display_installed_jobs_list_page(
            repository, data_manager_names=data_manager_name, strings_displayed=strings_displayed
        )

    def test_0040_verify_data_manager_data_table(self):
        """Verify that the installed repository populated shed_tool_data_table.xml and the sample files."""
        self.verify_installed_repository_data_table_entries(
            required_data_table_entries=["data_manager_test_data_table"]
        )
