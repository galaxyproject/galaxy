import logging

import pytest

from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

repository_name = "filtering_0000"
repository_description = "Galaxy's filtering tool for test 0000"
repository_long_description = "Long description of Galaxy's filtering tool for test 0000"

log = logging.getLogger(__name__)


class TestBasicRepositoryFeatures(ShedTwillTestCase):
    """Test core repository features."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts and login as an admin user."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.test_user_2_email, username=common.test_user_2_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0010_create_categories(self):
        """Create categories for this test suite"""
        self.create_category(
            name="Test 0000 Basic Repository Features 1", description="Test 0000 Basic Repository Features 1"
        )
        self.create_category(
            name="Test 0000 Basic Repository Features 2", description="Test 0000 Basic Repository Features 2"
        )

    def test_0015_create_repository(self):
        """Create the filtering repository"""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        category = self.populator.get_category_with_name("Test 0000 Basic Repository Features 1")
        strings_displayed = self.expect_repo_created_strings(repository_name)
        self.get_or_create_repository(
            name=repository_name,
            description=repository_description,
            long_description=repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=strings_displayed,
        )

    def test_0020_edit_repository(self):
        """Edit the repository name, description, and long description"""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        new_name = "renamed_filtering"
        new_description = "Edited filtering tool"
        new_long_description = "Edited long description"
        self.edit_repository_information(
            repository, repo_name=new_name, description=new_description, long_description=new_long_description
        )

    def test_0025_change_repository_category(self):
        """Change the categories associated with the filtering repository"""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.edit_repository_categories(
            repository,
            categories_to_add=["Test 0000 Basic Repository Features 2"],
            categories_to_remove=["Test 0000 Basic Repository Features 1"],
        )

    def test_0035_upload_filtering_1_1_0(self):
        """Upload filtering_1.1.0.tar to the repository"""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.commit_tar_to_repository(
            repository, "filtering/filtering_1.1.0.tar", commit_message="Uploaded filtering 1.1.0"
        )

    def test_0040_verify_repository(self):
        """Display basic repository pages"""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.check_for_valid_tools(repository, strings_displayed=["Filter1"])
        self.check_count_of_metadata_revisions_associated_with_repository(repository, metadata_count=1)
        tip = self.get_repository_tip(repository)
        tool_guid = f"{self.url.replace('http://', '').rstrip('/')}/repos/user1/filtering_0000/Filter1/1.1.0"
        tool_metadata_strings_displayed = [
            tool_guid,
            "1.1.0",  # The tool version.
            "Filter1",  # The tool ID.
            "Filter",  # The tool name.
            "data on any column using simple expressions",
        ]  # The tool description.
        tool_page_strings_displayed = ["Filter (version 1.1.0)"]
        self.check_repository_tools_for_changeset_revision(
            repository,
            tip,
            tool_metadata_strings_displayed=tool_metadata_strings_displayed,
            tool_page_strings_displayed=tool_page_strings_displayed,
        )
        self.check_repository_metadata(repository, tip_only=False)
        self.browse_repository(
            repository, strings_displayed=[f"Repository '{repository.name}' revision", "(repository tip)"]
        )
        strings = ["Uploaded filtering 1.1.0"]
        self.display_repository_clone_page(
            common.test_user_1_name,
            repository_name,
            strings_displayed=strings,
        )

    def test_0055_upload_filtering_txt_file(self):
        """Upload filtering.txt file associated with tool version 1.1.0."""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.add_file_to_repository(repository, "filtering/filtering_0000.txt")
        expected = "Readme file for filtering 1.1.0"
        self.display_manage_repository_page(repository, strings_displayed=[expected])

    def test_0060_upload_filtering_test_data(self):
        """Upload filtering test data."""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.add_tar_to_repository(repository, "filtering/filtering_test_data.tar")
        self.check_repository_metadata(repository, tip_only=True)

    def test_0065_upload_filtering_2_2_0(self):
        """Upload filtering version 2.2.0"""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.add_tar_to_repository(repository, "filtering/filtering_2.2.0.tar")

    def test_0070_verify_filtering_repository(self):
        """Verify the new tool versions and repository metadata."""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        tip = self.get_repository_tip(repository)
        self.check_for_valid_tools(repository)
        strings_displayed: list[str] = []
        self.display_manage_repository_page(repository, strings_displayed=strings_displayed)
        self.check_count_of_metadata_revisions_associated_with_repository(repository, metadata_count=2)
        tool_guid = f"{self.url.replace('http://', '').rstrip('/')}/repos/user1/filtering_0000/Filter1/2.2.0"
        tool_metadata_strings_displayed = [
            tool_guid,
            "2.2.0",  # The tool version.
            "Filter1",  # The tool ID.
            "Filter",  # The tool name.
            "data on any column using simple expressions",
        ]  # The tool description.
        tool_page_strings_displayed = ["Filter (version 2.2.0)"]
        self.check_repository_tools_for_changeset_revision(
            repository,
            tip,
            tool_metadata_strings_displayed=tool_metadata_strings_displayed,
            tool_page_strings_displayed=tool_page_strings_displayed,
        )
        self.check_repository_metadata(repository, tip_only=False)

    def test_0075_upload_readme_txt_file(self):
        """Upload readme.txt file associated with tool version 2.2.0."""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.add_file_to_repository(repository, "readme.txt")
        content = "This is a readme file."
        self.display_manage_repository_page(repository, strings_displayed=[content])
        # Verify that there is a different readme file for each metadata revision.
        readme_content = "Readme file for filtering 1.1.0"
        self.display_manage_repository_page(
            repository,
            strings_displayed=[
                readme_content,
                content,
            ],
        )

    def test_0080_delete_readme_txt_file(self):
        """Delete the readme.txt file."""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.delete_files_from_repository(repository, filenames=["readme.txt"])
        self.check_count_of_metadata_revisions_associated_with_repository(repository, metadata_count=2)
        readme_content = "Readme file for filtering 1.1.0"
        self.display_manage_repository_page(repository, strings_displayed=[readme_content])

    def test_0090_verify_repository_metadata(self):
        """Verify that resetting the metadata does not change it."""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.verify_unchanged_repository_metadata(repository)

    def test_0095_verify_reserved_repository_name_handling(self):
        """Check that reserved repository names are handled correctly."""
        category = self.populator.get_category_with_name("Test 0000 Basic Repository Features 1")
        error_message = (
            "The term 'repos' is a reserved word in the Tool Shed, so it cannot be used as a repository name."
        )
        with pytest.raises(AssertionError):
            self.get_or_create_repository(
                name="repos",
                description=repository_description,
                long_description=repository_long_description,
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[error_message],
            )

    def test_0100_verify_reserved_username_handling(self):
        """Check that reserved usernames are handled correctly."""
        self.login(email="baduser@bx.psu.edu", username="repos")
        test_user_1 = self.test_db_util.get_user("baduser@bx.psu.edu")
        assert test_user_1 is None, 'Creating user with public name "repos" succeeded.'

    def test_0105_contact_repository_owner(self):
        """"""
        # We no longer implement this.
        pass

    def test_0125_upload_new_readme_file(self):
        """Upload a new readme file to the filtering_0000 repository and verify that there is no error."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        # Upload readme.txt to the filtering_0000 repository and verify that it is now displayed.
        self.add_file_to_repository(repository, "filtering/readme.txt")
        content = "These characters should not"
        self.display_manage_repository_page(repository, strings_displayed=[content])

    def test_0130_verify_handling_of_invalid_characters(self):
        """Load the above changeset in the change log and confirm that there is no server error displayed."""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        changeset_revision = self.get_repository_tip(repository)
        repository_id = repository.id
        changelog_tuples = self.get_repository_changelog_tuples(repository)
        revision_number = -1
        revision_hash = "000000000000"
        for numeric_changeset, changeset_hash in changelog_tuples:
            if str(changeset_hash) == str(changeset_revision):
                revision_number = numeric_changeset
                revision_hash = changeset_hash
                break
        # Check for the changeset revision, repository name, owner username, 'repos' in the clone url, and the captured
        # unicode decoding error message.
        content = "These characters should not"
        strings_displayed = [
            f"{revision_number}:{revision_hash}",
            "filtering_0000",
            "user1",
            "repos",
            "added:",
            f"+{content}",
        ]
        self.load_changeset_in_tool_shed(repository_id, changeset_revision, strings_displayed=strings_displayed)

    def test_0135_api_get_repositories_in_category(self):
        """Load the api endpoint for repositories in a category."""
        categories = [
            self.populator.get_category_with_name(name)
            for name in ("Test 0000 Basic Repository Features 1", "Test 0000 Basic Repository Features 2")
        ]
        self.get_repositories_category_api(categories)

    def test_0140_view_invalid_changeset(self):
        """View repository using an invalid changeset"""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        encoded_repository_id = repository.id
        assert encoded_repository_id
        view_repo_url = (
            f"/repository/view_repository?id={encoded_repository_id}&changeset_revision=nonsensical_changeset"
        )
        self.visit_url(view_repo_url)
