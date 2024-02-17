import os

from ..base import common
from ..base.api import skip_if_api_v2
from ..base.twilltestcase import ShedTwillTestCase

repository_name = "freebayes_0010"
repository_description = "Galaxy's freebayes tool"
repository_long_description = "Long description of Galaxy's freebayes tool"

"""
1. Create repository freebayes_0020 and upload only the tool XML.
2. Upload the tool_data_table_conf.xml.sample file.
3. Upload sam_fa_indices.loc.sample.
4. Upload a tool_dependencies.xml file that should not parse correctly.
5. Upload a tool_dependencies.xml file that specifies a version that does not match the tool's requirements.
6. Upload a valid tool_dependencies.xml file.
7. Check for the appropriate strings on the manage repository page.
"""


class TestFreebayesRepository(ShedTwillTestCase):
    """Testing freebayes with tool data table entries, .loc files, and tool dependencies."""

    def test_0000_create_or_login_admin_user(self):
        """Create necessary user accounts and login as an admin user."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_category(self):
        """Create a category for this test suite"""
        self.create_category(
            name="Test 0010 Repository With Tool Dependencies",
            description="Tests for a repository with tool dependencies.",
        )

    def test_0010_create_freebayes_repository_and_upload_tool_xml(self):
        """Create freebayes repository and upload only freebayes.xml.

        We are at step 1 - Create repository freebayes_0020 and upload only the tool XML.
        Uploading only the tool XML file should result in an invalid tool and an error message on
        upload, as well as on the manage repository page.
        """
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        category = self.populator.get_category_with_name("Test 0010 Repository With Tool Dependencies")
        repository = self.get_or_create_repository(
            name=repository_name,
            description=repository_description,
            long_description=repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        strings_displayed = ["Metadata may have been defined", "This file requires an entry", "tool_data_table_conf"]
        self.add_file_to_repository(repository, "freebayes/freebayes.xml", strings_displayed=strings_displayed)
        if self.is_v2:
            # opps... not good right?
            self.populator.reset_metadata(repository)
        self.display_manage_repository_page(
            repository, strings_displayed=[self.invalid_tools_labels], strings_not_displayed=["Valid tools"]
        )
        tip = self.get_repository_tip(repository)
        strings_displayed = ["requires an entry", "tool_data_table_conf.xml"]
        self.check_repository_invalid_tools_for_changeset_revision(repository, tip, strings_displayed=strings_displayed)

    def test_0015_upload_missing_tool_data_table_conf_file(self):
        """Upload the missing tool_data_table_conf.xml.sample file to the repository.

        We are at step 2 - Upload the tool_data_table_conf.xml.sample file.
        Uploading the tool_data_table_conf.xml.sample alone should not make the tool valid, but the error message should change.
        """
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        strings_displayed = ["Upload a file named <b>sam_fa_indices.loc.sample"]
        self.add_file_to_repository(
            repository, "freebayes/tool_data_table_conf.xml.sample", strings_displayed=strings_displayed
        )
        self.display_manage_repository_page(
            repository, strings_displayed=[self.invalid_tools_labels], strings_not_displayed=["Valid tools"]
        )
        tip = self.get_repository_tip(repository)
        strings_displayed = ["refers to a file", "sam_fa_indices.loc"]
        self.check_repository_invalid_tools_for_changeset_revision(repository, tip, strings_displayed=strings_displayed)

    def test_0020_upload_missing_sample_loc_file(self):
        """Upload the missing sam_fa_indices.loc.sample file to the repository.

        We are at step 3 - Upload the tool_data_table_conf.xml.sample file.
        Uploading the tool_data_table_conf.xml.sample alone should not make the tool valid, but the error message should change.
        """
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.add_file_to_repository(repository, "freebayes/sam_fa_indices.loc.sample")

    def test_0025_upload_malformed_tool_dependency_xml(self):
        """Upload tool_dependencies.xml with bad characters in the readme tag.

        We are at step 4 - Upload a tool_dependencies.xml file that should not parse correctly.
        Upload a tool_dependencies.xml file that contains <> in the text of the readme tag. This should show an error message about malformed xml.
        """
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        target = os.path.join("freebayes", "malformed_tool_dependencies", "tool_dependencies.xml")
        self.add_file_to_repository(
            repository, target, strings_displayed=["Exception attempting to parse", "invalid element name"]
        )

    def test_0030_upload_invalid_tool_dependency_xml(self):
        """Upload tool_dependencies.xml defining version 0.9.5 of the freebayes package.

        We are at step 5 - Upload a tool_dependencies.xml file that specifies a version that does not match the tool's requirements.
        This should result in a message about the tool dependency configuration not matching the tool's requirements.
        """
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        target = os.path.join("freebayes", "invalid_tool_dependencies", "tool_dependencies.xml")
        strings_displayed = [
            "The settings for <b>name</b>, <b>version</b> and <b>type</b> from a contained tool configuration"
        ]
        self.add_file_to_repository(repository, target, strings_displayed=strings_displayed)

    def test_0035_upload_valid_tool_dependency_xml(self):
        """Upload tool_dependencies.xml defining version 0.9.4_9696d0ce8a962f7bb61c4791be5ce44312b81cf8 of the freebayes package.

        We are at step 6 - Upload a valid tool_dependencies.xml file.
        At this stage, there should be no errors on the upload page, as every missing or invalid file has been corrected.
        """
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        target = os.path.join("freebayes", "tool_dependencies.xml")
        self.add_file_to_repository(repository, target)

    @skip_if_api_v2
    def test_0040_verify_tool_dependencies(self):
        """Verify that the uploaded tool_dependencies.xml specifies the correct package versions.

        We are at step 7 - Check for the appropriate strings on the manage repository page.
        Verify that the manage repository page now displays the valid tool dependencies, and that there are no invalid tools shown on the manage page.
        """
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        strings_displayed = ["freebayes", "0.9.4_9696d0ce8a9", "samtools", "0.1.18", "Valid tools", "package"]
        strings_not_displayed = [self.invalid_tools_labels]
        self.display_manage_repository_page(
            repository, strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed
        )
