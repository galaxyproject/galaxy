from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

column_maker_repository_name = "column_maker_0110"
column_maker_repository_description = "A flexible aligner."
column_maker_repository_long_description = "A flexible aligner and methylation caller for Bisulfite-Seq applications."

emboss_repository_name = "emboss_0110"
emboss_repository_description = "Galaxy wrappers for Emboss version 5.0.0 tools"
emboss_repository_long_description = "Galaxy wrappers for Emboss version 5.0.0 tools"

category_name = "Test 0110 Invalid Repository Dependencies"
category_desc = "Test 0110 Invalid Repository Dependencies"
running_standalone = False


class TestBasicRepositoryDependencies(ShedTwillTestCase):
    """Testing emboss 5 with repository dependencies."""

    requires_galaxy = True

    def test_0000_initiate_users(self):
        """Create necessary user accounts and login as an admin user."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_category(self):
        """Create a category for this test suite"""
        self.create_category(name=category_name, description=category_desc)

    def test_0010_create_emboss_dependendent_column_maker_repository_and_upload_tarball(self):
        """Create and populate the column_maker repository."""
        global running_standalone
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        category = self.populator.get_category_with_name(category_name)
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
            self.commit_tar_to_repository(
                column_maker_repository,
                "column_maker/column_maker.tar",
                commit_message="Uploaded column_maker tarball.",
            )

    def test_0020_create_emboss_5_repository_and_upload_files(self):
        """Create and populate the emboss_5_0110 repository."""
        if running_standalone:
            category = self.populator.get_category_with_name(category_name)
            repository = self.get_or_create_repository(
                name=emboss_repository_name,
                description=emboss_repository_description,
                long_description=emboss_repository_long_description,
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                repository,
                "emboss/emboss.tar",
                commit_message="Uploaded emboss tool tarball.",
            )

    def test_0025_generate_repository_dependency_with_invalid_url(self):
        """Generate a repository dependency for emboss 5 with an invalid URL."""
        if running_standalone:
            dependency_path = self.generate_temp_path("test_1110", additional_paths=["simple"])
            column_maker_repository = self._get_repository_by_name_and_owner(
                column_maker_repository_name, common.test_user_1_name
            )
            emboss_repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
            url = "http://http://this is not an url!"
            name = column_maker_repository.name
            owner = column_maker_repository.owner
            changeset_revision = self.get_repository_tip(column_maker_repository)
            strings_displayed = ["Repository dependencies are currently supported only within the same tool shed"]
            repository_tuple = (url, name, owner, changeset_revision)
            self.create_repository_dependency(
                repository=emboss_repository,
                filepath=dependency_path,
                repository_tuples=[repository_tuple],
                strings_displayed=strings_displayed,
                complex=False,
            )

    def test_0030_generate_repository_dependency_with_invalid_name(self):
        """Generate a repository dependency for emboss 5 with an invalid name."""
        if running_standalone:
            dependency_path = self.generate_temp_path("test_1110", additional_paths=["simple"])
            repository = self._get_repository_by_name_and_owner(column_maker_repository_name, common.test_user_1_name)
            emboss_repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
            url = self.url
            name = "!?invalid?!"
            owner = repository.owner
            changeset_revision = self.get_repository_tip(repository)
            strings_displayed = ["because the name is invalid."]
            repository_tuple = (url, name, owner, changeset_revision)
            self.create_repository_dependency(
                repository=emboss_repository,
                filepath=dependency_path,
                repository_tuples=[repository_tuple],
                strings_displayed=strings_displayed,
                complex=False,
            )

    def test_0035_generate_repository_dependency_with_invalid_owner(self):
        """Generate a repository dependency for emboss 5 with an invalid owner."""
        if running_standalone:
            dependency_path = self.generate_temp_path("test_1110", additional_paths=["simple"])
            repository = self._get_repository_by_name_and_owner(column_maker_repository_name, common.test_user_1_name)
            emboss_repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
            url = self.url
            name = repository.name
            owner = "!?invalid?!"
            changeset_revision = self.get_repository_tip(repository)
            strings_displayed = ["because the owner is invalid."]
            repository_tuple = (url, name, owner, changeset_revision)
            self.create_repository_dependency(
                repository=emboss_repository,
                filepath=dependency_path,
                repository_tuples=[repository_tuple],
                strings_displayed=strings_displayed,
                complex=False,
            )

    def test_0040_generate_repository_dependency_with_invalid_changeset_revision(self):
        """Generate a repository dependency for emboss 5 with an invalid changeset revision."""
        if running_standalone:
            dependency_path = self.generate_temp_path("test_1110", additional_paths=["simple", "invalid"])
            repository = self._get_repository_by_name_and_owner(column_maker_repository_name, common.test_user_1_name)
            emboss_repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
            url = self.url
            name = repository.name
            owner = repository.owner
            changeset_revision = "!?invalid?!"
            strings_displayed = ["because the changeset revision is invalid."]
            repository_tuple = (url, name, owner, changeset_revision)
            self.create_repository_dependency(
                repository=emboss_repository,
                filepath=dependency_path,
                repository_tuples=[repository_tuple],
                strings_displayed=strings_displayed,
                complex=False,
            )

    def test_0045_install_repository_with_invalid_repository_dependency(self):
        """Install the repository and verify that galaxy detects invalid repository dependencies."""
        repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
        preview_strings_displayed = [
            "emboss_0110",
            self.get_repository_tip(repository),
            "Ignoring repository dependency definition",
        ]
        self._install_repository(
            emboss_repository_name,
            common.test_user_1_name,
            category_name,
            install_tool_dependencies=False,
            install_repository_dependencies=True,
            preview_strings_displayed=preview_strings_displayed,
        )
        installed_repository = self._get_installed_repository_by_name_owner(
            emboss_repository_name, common.test_user_1_name
        )
        json = self.display_installed_repository_manage_json(installed_repository)
        assert "repository_dependencies" not in json
