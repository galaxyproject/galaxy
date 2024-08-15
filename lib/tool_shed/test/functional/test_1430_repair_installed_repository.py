import logging

from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

log = logging.getLogger(__name__)

category_name = "Test 1430 Repair installed repository"
category_description = "Test script 1430 for repairing an installed repository."
filter_repository_name = "filter_1430"
column_repository_name = "column_1430"
filter_repository_description = "Galaxy's filter tool for test 1430"
column_repository_description = "Add a value as a new column"
filter_repository_long_description = f"{filter_repository_name}: {filter_repository_description}"
column_repository_long_description = f"{column_repository_name}: {column_repository_description}"

"""
In the Tool Shed:

1) Create and populate the filter_1430 repository

2) Create and populate the column_1430 repository

3) Upload a repository_dependencies.xml file to the column_1430 repository that creates a repository dependency on the filter_1430 repository.

In Galaxy:

1) Install the column_1430 repository, making sure to check the checkbox to Handle repository dependencies so that the filter
   repository is also installed. Make sure to install the repositories in a specified section of the tool panel.

2) Uninstall the filter_1430 repository.
"""


class TestRepairRepository(ShedTwillTestCase):
    """Test repairing an installed repository."""

    requires_galaxy = True

    def test_0000_initiate_users_and_category(self):
        """Create necessary user accounts and login as an admin user."""
        self.login(email=common.admin_email, username=common.admin_username)
        self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_2_email, username=common.test_user_2_name)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)

    def test_0005_create_filter_repository(self):
        """Create and populate the filter_1430 repository.

        This is step 1 - Create and populate the filter_1430 repository.

        This repository will be depended on by the column_1430 repository.
        """
        category = self.populator.get_category_with_name(category_name)
        repository = self.get_or_create_repository(
            name=filter_repository_name,
            description=filter_repository_description,
            long_description=filter_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        self.commit_tar_to_repository(
            repository,
            "filtering/filtering_1.1.0.tar",
            commit_message="Populate filter_1430 with version 1.1.0.",
        )

    def test_0010_create_column_repository(self):
        """Create and populate the column_1430 repository.

        This is step 2 - Create and populate the column_1430 repository.

        This repository will depend on the filter_1430 repository.
        """
        category = self.populator.get_category_with_name(category_name)
        repository = self.get_or_create_repository(
            name=column_repository_name,
            description=column_repository_description,
            long_description=column_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        self.commit_tar_to_repository(
            repository,
            "column_maker/column_maker.tar",
            commit_message="Populate column_1430 with tool definitions.",
        )

    def test_0015_create_repository_dependency(self):
        """Create a dependency on filter_1430.

        This is step 3 - Upload a repository_dependencies.xml file to the column_1430 repository that creates a repository
        dependency on the filter_1430 repository.
        """
        column_repository = self._get_repository_by_name_and_owner("column_1430", common.test_user_1_name)
        filter_repository = self._get_repository_by_name_and_owner("filter_1430", common.test_user_1_name)
        tool_shed_url = self.url
        name = filter_repository.name
        owner = filter_repository.owner
        changeset_revision = self.get_repository_tip(filter_repository)
        repository_dependency_tuple = (tool_shed_url, name, owner, changeset_revision)
        filepath = self.generate_temp_path("1430_repository_dependency")
        self.create_repository_dependency(column_repository, [repository_dependency_tuple], filepath=filepath)

    def test_0020_install_column_repository(self):
        """Install the column_1430 repository into Galaxy.

        This is step 1 (galaxy side) - Install the column_1430 repository, making sure to check the checkbox to
        handle repository dependencies so that the filter_1430 repository is also installed. Make sure to install
        the repositories in a specified section of the tool panel.
        """
        self._install_repository(
            "column_1430",
            common.test_user_1_name,
            category_name,
            new_tool_panel_section_label="repair",
            install_tool_dependencies=False,
            install_repository_dependencies=True,
        )

    def test_0025_uninstall_filter_repository(self):
        """Uninstall the filter_1430 repository from Galaxy.

        This is step 2 - Uninstall the filter_1430 repository.
        """
        installed_repository = self._get_installed_repository_by_name_owner("filter_1430", common.test_user_1_name)
        self._uninstall_repository(installed_repository)
        self._assert_has_no_installed_repos_with_names("filter_1430")
