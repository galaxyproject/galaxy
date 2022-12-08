import logging
import os

from ..base.twilltestcase import (
    common,
    ShedTwillTestCase,
)

repository_name = "freebayes_0010"
repository_description = "Galaxy's freebayes tool"
repository_long_description = "Long description of Galaxy's freebayes tool"
category_name = "Test 0010 Repository With Tool Dependencies"
log = logging.getLogger(__name__)


class TestToolWithToolDependencies(ShedTwillTestCase):
    """Test installing a repository with tool dependencies."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.galaxy_login(email=common.admin_email, username=common.admin_username)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_ensure_repositories_and_categories_exist(self):
        """Create the 0010 category and upload the freebayes repository to it, if necessary."""
        category = self.create_category(
            name=category_name, description="Tests for a repository with tool dependencies."
        )
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name=repository_name,
            description=repository_description,
            long_description=repository_long_description,
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

    def test_0010_browse_tool_shed(self):
        """Browse the available tool sheds in this Galaxy instance and preview the freebayes tool."""
        self.galaxy_login(email=common.admin_email, username=common.admin_username)
        self.browse_tool_shed(url=self.url, strings_displayed=[category_name])
        category = self.populator.get_category_with_name(category_name)
        self.browse_category(category, strings_displayed=[repository_name])
        strings_displayed = [repository_name, "Valid tools", "Tool dependencies"]
        self.preview_repository_in_tool_shed(
            repository_name, common.test_user_1_name, strings_displayed=strings_displayed
        )

    def test_0015_install_freebayes_repository(self):
        """Install the freebayes repository without installing tool dependencies."""
        self._install_repository(
            repository_name,
            common.test_user_1_name,
            category_name,
            install_tool_dependencies=False,
            new_tool_panel_section_label="test_1010",
        )
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            repository_name, common.test_user_1_name
        )
        assert self.get_installed_repository_for(
            common.test_user_1, repository_name, installed_repository.installed_changeset_revision
        )
        self._assert_has_valid_tool_with_name("FreeBayes")
        self._assert_repo_has_tool_with_id(installed_repository, "freebayes")

    def test_0020_verify_installed_repository_metadata(self):
        """Verify that resetting the metadata on an installed repository does not change the metadata."""
        self.verify_installed_repository_metadata_unchanged(repository_name, common.test_user_1_name)

    def test_0025_verify_sample_files(self):
        """Verify that the installed repository populated shed_tool_data_table.xml and the sample files."""
        self.verify_installed_repository_data_table_entries(required_data_table_entries=["sam_fa_indexes"])
