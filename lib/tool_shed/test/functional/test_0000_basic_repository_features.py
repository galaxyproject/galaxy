import logging

import pytest

from ..base import common
from ..base.api import skip_if_api_v2
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

    @skip_if_api_v2
    # no replicating the functionality in tool shed 2.0, use Planemo
    # to create repositories.
    def test_0005_create_repository_without_categories(self):
        """Verify that a repository cannot be created unless at least one category has been defined."""
        strings_displayed = ["No categories have been configured in this instance of the Galaxy Tool Shed"]
        self.visit_url("/repository/create_repository")
        self.check_for_strings(strings_displayed=strings_displayed, strings_not_displayed=[])

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

    @skip_if_api_v2
    def test_0030_grant_write_access(self):
        """Grant write access to another user"""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.grant_write_access(repository, usernames=[common.test_user_2_name])
        self.revoke_write_access(repository, common.test_user_2_name)

    def test_0035_upload_filtering_1_1_0(self):
        """Upload filtering_1.1.0.tar to the repository"""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.commit_tar_to_repository(
            repository, "filtering/filtering_1.1.0.tar", commit_message="Uploaded filtering 1.1.0"
        )

    def test_0040_verify_repository(self):
        """Display basic repository pages"""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        latest_changeset_revision = self.get_repository_tip(repository)
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
        if self._browser.is_twill:
            # this appears in a link - it isn't how one would check this
            # in playwright. But also we're testing the mercurial page
            # here so this is probably a questionable check overall.
            strings += [latest_changeset_revision]
        self.display_repository_clone_page(
            common.test_user_1_name,
            repository_name,
            strings_displayed=strings,
        )

    @skip_if_api_v2
    def test_0045_alter_repository_states(self):
        """Test toggling the malicious and deprecated repository flags."""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)
        self.set_repository_malicious(
            repository, set_malicious=True, strings_displayed=["The repository tip has been defined as malicious."]
        )
        self.set_repository_malicious(
            repository,
            set_malicious=False,
            strings_displayed=["The repository tip has been defined as <b>not</b> malicious."],
        )
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.set_repository_deprecated(repository, strings_displayed=["has been marked as deprecated"])
        strings_displayed = ["This repository has been marked as deprecated", "Mark repository as not deprecated"]
        self.display_manage_repository_page(
            repository,
            strings_displayed=strings_displayed,
            strings_not_displayed=["Reset all repository metadata"],
        )
        self.browse_repository(repository)
        self.set_repository_deprecated(
            repository, strings_displayed=["has been marked as not deprecated"], set_deprecated=False
        )
        strings_displayed = ["Mark repository as deprecated", "Reset all repository metadata"]
        self.display_manage_repository_page(repository, strings_displayed=strings_displayed)

    @skip_if_api_v2
    # probably not porting this functionality - just test
    # with Twill for older UI and drop when that is all dropped
    def test_0050_display_repository_tip_file(self):
        """Display the contents of filtering.xml in the repository tip revision"""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        if self._browser.is_twill:
            self.display_repository_file_contents(
                repository=repository,
                filename="filtering.xml",
                filepath=None,
                strings_displayed=["1.1.0"],
                strings_not_displayed=[],
            )

    def test_0055_upload_filtering_txt_file(self):
        """Upload filtering.txt file associated with tool version 1.1.0."""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.add_file_to_repository(repository, "filtering/filtering_0000.txt")
        expected = self._escape_page_content_if_needed("Readme file for filtering 1.1.0")
        self.display_manage_repository_page(repository, strings_displayed=[expected])

    def test_0060_upload_filtering_test_data(self):
        """Upload filtering test data."""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.add_tar_to_repository(repository, "filtering/filtering_test_data.tar")
        if self._browser.is_twill:
            # probably not porting this functionality - just test
            # with Twill for older UI and drop when that is all dropped
            self.display_repository_file_contents(
                repository=repository,
                filename="1.bed",
                filepath="test-data",
                strings_displayed=[],
                strings_not_displayed=[],
            )
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
        if self.is_v2:
            strings_displayed = []
        else:
            strings_displayed = ["Select a revision"]
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
        content = self._escape_page_content_if_needed("This is a readme file.")
        self.display_manage_repository_page(repository, strings_displayed=[content])
        # Verify that there is a different readme file for each metadata revision.
        readme_content = self._escape_page_content_if_needed("Readme file for filtering 1.1.0")
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
        readme_content = self._escape_page_content_if_needed("Readme file for filtering 1.1.0")
        self.display_manage_repository_page(repository, strings_displayed=[readme_content])

    @skip_if_api_v2  # not re-implemented in the UI, there are API tests though
    def test_0085_search_for_valid_filter_tool(self):
        """Search for the filtering tool by tool ID, name, and version."""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        tip_changeset = self.get_repository_tip(repository)
        search_fields = dict(tool_id="Filter1", tool_name="filter", tool_version="2.2.0")
        self.search_for_valid_tools(
            search_fields=search_fields, strings_displayed=[tip_changeset], strings_not_displayed=[]
        )

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
        if not self.is_v2:
            # no longer use this terminology but the above test case ensures
            # the important thing and caught a bug in v2
            error_message = (
                "The term 'repos' is a reserved word in the Tool Shed, so it cannot be used as a public user name."
            )
            self.check_for_strings(strings_displayed=[error_message])

    def test_0105_contact_repository_owner(self):
        """"""
        # We no longer implement this.
        pass

    @skip_if_api_v2  # v2 doesn't implement repository deleting repositories
    def test_0110_delete_filtering_repository(self):
        """Delete the filtering_0000 repository and verify that it no longer has any downloadable revisions."""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)
        self.delete_repository(repository)
        metadata = self.populator.get_metadata(repository, downloadable_only=False)
        for _, value in metadata.root.items():
            assert not value.downloadable
        # Explicitly reload all metadata revisions from the database, to ensure that we have the current status of the downloadable flag.
        # for metadata_revision in repository.metadata_revisions:
        #    self.test_db_util.refresh(metadata_revision)
        # Marking a repository as deleted should result in no metadata revisions being downloadable.
        # assert True not in [metadata.downloadable for metadata in self._db_repository(repository).metadata_revisions]

    @skip_if_api_v2  # v2 doesn't implement repository deleting repositories
    def test_0115_undelete_filtering_repository(self):
        """Undelete the filtering_0000 repository and verify that it now has two downloadable revisions."""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)
        self.undelete_repository(repository)
        # Explicitly reload all metadata revisions from the database, to ensure that we have the current status of the downloadable flag.
        # for metadata_revision in repository.metadata_revisions:
        #    self.test_db_util.refresh(metadata_revision)
        # Marking a repository as undeleted should result in all previously downloadable metadata revisions being downloadable again.
        # In this case, there should be two downloadable revisions, one for filtering 1.1.0 and one for filtering 2.2.0.
        assert True in [metadata.downloadable for metadata in self._db_repository(repository).metadata_revisions]
        assert len(self._db_repository(repository).downloadable_revisions) == 2

    @skip_if_api_v2  # not re-implementing in tool shed 2.0
    def test_0120_enable_email_notifications(self):
        """Enable email notifications for test user 2 on filtering_0000."""
        # Log in as test_user_2
        self.login(email=common.test_user_2_email, username=common.test_user_2_name)
        # Get the repository, so we can pass the encoded repository id and browse_repositories method to the set_email_alerts method.
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        strings_displayed = ["Total alerts added: 1, total alerts removed: 0"]
        self.enable_email_alerts(repository, strings_displayed=strings_displayed)

    def test_0125_upload_new_readme_file(self):
        """Upload a new readme file to the filtering_0000 repository and verify that there is no error."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        # Upload readme.txt to the filtering_0000 repository and verify that it is now displayed.
        self.add_file_to_repository(repository, "filtering/readme.txt")
        content = self._escape_page_content_if_needed("These characters should not")
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
        content = self._escape_page_content_if_needed("These characters should not")
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
        strings_displayed = ["Invalid+changeset+revision"]
        view_repo_url = (
            f"/repository/view_repository?id={encoded_repository_id}&changeset_revision=nonsensical_changeset"
        )
        self.visit_url(view_repo_url)
        if self._browser.is_twill:
            self.check_for_strings(strings_displayed=strings_displayed, strings_not_displayed=[])
