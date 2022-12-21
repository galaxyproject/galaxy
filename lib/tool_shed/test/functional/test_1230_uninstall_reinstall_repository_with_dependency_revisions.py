from ..base.twilltestcase import (
    common,
    ShedTwillTestCase,
)

column_maker_repository_name = "column_maker_0030"
column_maker_repository_description = "Add column"
column_maker_repository_long_description = "Compute an expression on every row"

emboss_repository_name = "emboss_0030"
emboss_5_repository_name = "emboss_5_0030"
emboss_6_repository_name = "emboss_6_0030"
emboss_repository_description = "Galaxy wrappers for Emboss version 5.0.0 tools"
emboss_repository_long_description = "Galaxy wrappers for Emboss version 5.0.0 tools"

running_standalone = False


class TestUninstallingAndReinstallingRepositories(ShedTwillTestCase):
    """Test uninstalling and reinstalling a repository with repository dependency revisions."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.galaxy_login(email=common.admin_email, username=common.admin_username)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_ensure_repositories_and_categories_exist(self):
        """Create the 0030 category and upload the emboss repository to the tool shed, if necessary."""
        global running_standalone
        category = self.create_category(
            name="Test 0030 Repository Dependency Revisions",
            description="Tests for a repository with tool dependencies.",
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
            running_standalone = True
            emboss_5_repository = self.get_or_create_repository(
                name=emboss_5_repository_name,
                description=emboss_repository_description,
                long_description=emboss_repository_long_description,
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.upload_file(
                column_maker_repository,
                filename="column_maker/column_maker.tar",
                filepath=None,
                valid_tools_only=False,
                uncompress_file=True,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded bismark tarball.",
                strings_displayed=[],
                strings_not_displayed=[],
            )
            repository_dependencies_path = self.generate_temp_path("test_1030", additional_paths=["emboss", "5"])
            column_maker_tuple = (
                self.url,
                column_maker_repository.name,
                column_maker_repository.owner,
                self.get_repository_tip(column_maker_repository),
            )
            self.create_repository_dependency(
                repository=emboss_5_repository,
                repository_tuples=[column_maker_tuple],
                filepath=repository_dependencies_path,
            )
            emboss_6_repository = self.get_or_create_repository(
                name=emboss_6_repository_name,
                description=emboss_repository_description,
                long_description=emboss_repository_long_description,
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.upload_file(
                emboss_6_repository,
                filename="emboss/emboss.tar",
                filepath=None,
                valid_tools_only=True,
                uncompress_file=False,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded tool tarball.",
                strings_displayed=[],
                strings_not_displayed=[],
            )
            repository_dependencies_path = self.generate_temp_path("test_1030", additional_paths=["emboss", "6"])
            column_maker_tuple = (
                self.url,
                column_maker_repository.name,
                column_maker_repository.owner,
                self.get_repository_tip(column_maker_repository),
            )
            self.create_repository_dependency(
                repository=emboss_6_repository,
                repository_tuples=[column_maker_tuple],
                filepath=repository_dependencies_path,
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
                uncompress_file=False,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded tool tarball.",
                strings_displayed=[],
                strings_not_displayed=[],
            )
            repository_dependencies_path = self.generate_temp_path("test_1030", additional_paths=["emboss", "5"])
            dependency_tuple = (
                self.url,
                emboss_5_repository.name,
                emboss_5_repository.owner,
                self.get_repository_tip(emboss_5_repository),
            )
            self.create_repository_dependency(
                repository=emboss_repository,
                repository_tuples=[dependency_tuple],
                filepath=repository_dependencies_path,
            )
            dependency_tuple = (
                self.url,
                emboss_6_repository.name,
                emboss_6_repository.owner,
                self.get_repository_tip(emboss_6_repository),
            )
            self.create_repository_dependency(
                repository=emboss_repository,
                repository_tuples=[dependency_tuple],
                filepath=repository_dependencies_path,
            )

    def test_0010_install_emboss_repository(self):
        """Install the emboss repository into the Galaxy instance."""
        global running_standalone
        self.galaxy_login(email=common.admin_email, username=common.admin_username)
        self._install_repository(
            emboss_repository_name,
            common.test_user_1_name,
            "Test 0030 Repository Dependency Revisions",
            new_tool_panel_section_label="test_1210",
        )
        self._assert_has_installed_repos_with_names(emboss_repository_name)

    def test_0015_uninstall_emboss_repository(self):
        """Uninstall the emboss repository."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            emboss_repository_name, common.test_user_1_name
        )
        self.uninstall_repository(installed_repository)
        self._assert_has_no_installed_repos_with_names(emboss_repository_name)

    def test_0020_reinstall_emboss_repository(self):
        """Reinstall the emboss repository."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            emboss_repository_name, common.test_user_1_name
        )
        self.reinstall_repository_api(installed_repository)
        self._assert_has_installed_repos_with_names(emboss_repository_name)
        self._assert_has_valid_tool_with_name("emboss")

    def test_0025_deactivate_emboss_repository(self):
        """Deactivate the emboss repository without removing it from disk."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            emboss_repository_name, common.test_user_1_name
        )
        self.deactivate_repository(installed_repository)
        self._assert_has_no_installed_repos_with_names(emboss_repository_name)

    def test_0030_reactivate_emboss_repository(self):
        """Reactivate the emboss repository and verify that it now shows up in the list of installed repositories."""
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner(
            emboss_repository_name, common.test_user_1_name
        )
        self.reactivate_repository(installed_repository)
        self._assert_has_installed_repos_with_names(emboss_repository_name)
        self._assert_has_valid_tool_with_name("emboss")
        self._assert_repo_has_tool_with_id(installed_repository, "EMBOSS: antigenic1")
