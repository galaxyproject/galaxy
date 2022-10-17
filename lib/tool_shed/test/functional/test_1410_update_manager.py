import logging
import time

from ..base.twilltestcase import (
    common,
    ShedTwillTestCase,
)

log = logging.getLogger(__name__)

repository_name = "filtering_1410"
repository_description = "Galaxy's filtering tool"
repository_long_description = "Long description of Galaxy's filtering repository"

category_name = "Test 1410 - Galaxy Update Manager"
category_description = "Functional test suite to test the update manager."

"""
1. Create and populate the filtering_1410 repository.
2. Install filtering_1410 to Galaxy.
3. Upload a readme file.
4. Verify that the browse page now shows an update available.
"""


class TestUpdateManager(ShedTwillTestCase):
    """Test the Galaxy update manager."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts and login as an admin user.

        Create all the user accounts that are needed for this test script to run independently of other tests.
        Previously created accounts will not be re-created.
        """
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)
        self.galaxy_login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_filtering_repository(self):
        """Create and populate the filtering_1410 repository.

        We are at step 1 - Create and populate the filtering_1410 repository.
        Create filtering_1410 and upload the tool tarball to it.
        """
        self.login(email=common.admin_email, username=common.admin_username)
        category = self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name=repository_name,
            description=repository_description,
            long_description=repository_long_description,
            owner=common.test_user_1_name,
            category=category,
        )
        self.upload_file(
            repository,
            filename="filtering/filtering_1.1.0.tar",
            filepath=None,
            valid_tools_only=True,
            uncompress_file=True,
            remove_repo_files_not_in_tar=True,
            commit_message="Uploaded filtering 1.1.0",
            strings_displayed=[],
            strings_not_displayed=[],
        )

    def test_0010_install_filtering_repository(self):
        """Install the filtering_1410 repository.

        We are at step 2 - Install filtering_1410 to Galaxy.
        Install the filtering repository to Galaxy.
        """
        self.galaxy_login(email=common.admin_email, username=common.admin_username)
        self._install_repository(
            repository_name, common.test_user_1_name, category_name, new_tool_panel_section_label="test_1410"
        )
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            repository_name, common.test_user_1_name
        )
        self._assert_has_installed_repos_with_names(repository_name)
        self._assert_has_valid_tool_with_name("Filter")
        self._assert_repo_has_tool_with_id(installed_repository, "Filter1")

    def test_0015_upload_readme_file(self):
        """Upload readme.txt to filtering_1410.

        We are at step 3 - Upload a readme file.
        Upload readme.txt. This will have the effect of making the installed changeset revision not be the most recent downloadable revision,
        but without generating a second downloadable revision. Then sleep for 3 seconds to make sure the update manager picks up the new
        revision.
        """
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.upload_file(
            repository,
            filename="readme.txt",
            filepath=None,
            valid_tools_only=True,
            uncompress_file=True,
            remove_repo_files_not_in_tar=False,
            commit_message="Uploaded readme.txt",
            strings_displayed=[],
            strings_not_displayed=[],
        )

    def test_0020_check_for_displayed_update(self):
        """Browse installed repositories and verify update.

        We are at step 4 - Verify that the browse page now shows an update available.
        The browse page should now show filtering_1410 as installed, but with a yellow box indicating that there is an update available.
        """
        # Wait 3 seconds, just to be sure we're past hours_between_check.
        time.sleep(3)
        self.galaxy_login(email=common.admin_email, username=common.admin_username)
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            repository_name, common.test_user_1_name
        )
        response = self.update_installed_repository_api(installed_repository)
        assert response["status"] == "ok"
        assert "has been updated" in response["message"]
