from ..base.twilltestcase import (
    common,
    ShedTwillTestCase,
)

column_maker_repository_name = "column_maker_0020"
column_maker_repository_description = "A flexible aligner."
column_maker_repository_long_description = "A flexible aligner and methylation caller for Bisulfite-Seq applications."

emboss_repository_name = "emboss_0020"
emboss_repository_description = "Galaxy wrappers for Emboss version 5.0.0 tools for test 0020"
emboss_repository_long_description = "Galaxy wrappers for Emboss version 5.0.0 tools for test 0020"


class TestToolWithRepositoryDependencies(ShedTwillTestCase):
    """Test installing a repository with repository dependencies."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)
        self.galaxy_login(email=common.admin_email, username=common.admin_username)

    def test_0005_ensure_repositories_and_categories_exist(self):
        """Create the 0020 category and any missing repositories."""
        category = self.create_category(
            name="Test 0020 Basic Repository Dependencies", description="Test 0020 Basic Repository Dependencies"
        )
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        column_maker_repository = self.get_or_create_repository(
            name=column_maker_repository_name,
            description=column_maker_repository_description,
            long_description=column_maker_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(column_maker_repository):
            self.upload_file(
                column_maker_repository,
                filename="column_maker/column_maker.tar",
                filepath=None,
                valid_tools_only=True,
                uncompress_file=True,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded column_maker tarball.",
                strings_displayed=[],
                strings_not_displayed=[],
            )
            emboss_repository = self.get_or_create_repository(
                name=emboss_repository_name,
                description=emboss_repository_description,
                long_description=emboss_repository_long_description,
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.upload_file(
                emboss_repository,
                filename="emboss/emboss.tar",
                filepath=None,
                valid_tools_only=True,
                uncompress_file=True,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded emboss.tar",
                strings_displayed=[],
                strings_not_displayed=[],
            )
            repository_dependencies_path = self.generate_temp_path("test_1020", additional_paths=["emboss", "5"])
            repository_tuple = (
                self.url,
                column_maker_repository.name,
                column_maker_repository.owner,
                self.get_repository_tip(column_maker_repository),
            )
            self.create_repository_dependency(
                repository=emboss_repository,
                repository_tuples=[repository_tuple],
                filepath=repository_dependencies_path,
            )

    def test_0010_browse_tool_shed(self):
        """Browse the available tool sheds in this Galaxy instance and preview the emboss tool."""
        self.galaxy_login(email=common.admin_email, username=common.admin_username)
        self.browse_tool_shed(url=self.url, strings_displayed=["Test 0020 Basic Repository Dependencies"])
        category = self.populator.get_category_with_name("Test 0020 Basic Repository Dependencies")
        self.browse_category(category, strings_displayed=[emboss_repository_name])
        self.preview_repository_in_tool_shed(
            emboss_repository_name, common.test_user_1_name, strings_displayed=[emboss_repository_name, "Valid tools"]
        )

    def test_0015_install_emboss_repository(self):
        """Install the emboss repository without installing tool dependencies."""
        self._install_repository(
            emboss_repository_name,
            common.test_user_1_name,
            "Test 0020 Basic Repository Dependencies",
            install_tool_dependencies=False,
            new_tool_panel_section_label="test_1020",
        )
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            emboss_repository_name, common.test_user_1_name
        )
        assert self.get_installed_repository_for(
            common.test_user_1, emboss_repository_name, installed_repository.installed_changeset_revision
        )
        self._assert_has_valid_tool_with_name("antigenic")
        self._assert_repo_has_tool_with_id(installed_repository, "EMBOSS: antigenic1")

    def test_0020_verify_installed_repository_metadata(self):
        """Verify that resetting the metadata on an installed repository does not change the metadata."""
        self.verify_installed_repository_metadata_unchanged(emboss_repository_name, common.test_user_1_name)

    def test_0025_deactivate_datatypes_repository(self):
        """Deactivate the emboss_datatypes repository without removing it from disk."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            column_maker_repository_name, common.test_user_1_name
        )
        self.deactivate_repository(installed_repository)

    def test_0030_reactivate_datatypes_repository(self):
        """Reactivate the datatypes repository and verify that the datatypes are again present."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            column_maker_repository_name, common.test_user_1_name
        )
        self.reactivate_repository(installed_repository)
        # This used to reactive datatype repositories and verify counts...
        # test may be considerably less useful now.
