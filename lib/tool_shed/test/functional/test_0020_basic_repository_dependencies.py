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


class TestBasicRepositoryDependencies(ShedTwillTestCase):
    """Testing emboss 5 with repository dependencies."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts and login as an admin user."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_category(self):
        """Create a category for this test suite"""
        self.create_category(
            name="Test 0020 Basic Repository Dependencies", description="Testing basic repository dependency features."
        )

    def test_0010_create_column_maker_repository(self):
        """Create and populate column_maker_0020."""
        category = self.populator.get_category_with_name("Test 0020 Basic Repository Dependencies")
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        column_maker_repository = self.get_or_create_repository(
            name=column_maker_repository_name,
            description=column_maker_repository_description,
            long_description=column_maker_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
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

    def test_0020_create_emboss_5_repository_and_upload_files(self):
        """Create and populate the emboss_5_0020 repository."""
        category = self.populator.get_category_with_name("Test 0020 Basic Repository Dependencies")
        repository = self.get_or_create_repository(
            name=emboss_repository_name,
            description=emboss_repository_description,
            long_description=emboss_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        self.upload_file(
            repository,
            filename="emboss/emboss.tar",
            filepath=None,
            valid_tools_only=True,
            uncompress_file=True,
            remove_repo_files_not_in_tar=False,
            commit_message="Uploaded emboss.tar",
            strings_displayed=[],
            strings_not_displayed=[],
        )

    def test_0025_generate_and_upload_repository_dependencies_xml(self):
        """Generate and upload the repository_dependencies.xml file"""
        repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
        column_maker_repository = self._get_repository_by_name_and_owner(
            column_maker_repository_name, common.test_user_1_name
        )
        repository_dependencies_path = self.generate_temp_path("test_0020", additional_paths=["emboss", "5"])
        repository_tuple = (
            self.url,
            column_maker_repository.name,
            column_maker_repository.owner,
            self.get_repository_tip(column_maker_repository),
        )
        self.create_repository_dependency(
            repository=repository, repository_tuples=[repository_tuple], filepath=repository_dependencies_path
        )

    def test_0030_verify_emboss_5_dependencies(self):
        """Verify that the emboss_5 repository now depends on the emboss_datatypes repository with correct name, owner, and changeset revision."""
        repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
        column_maker_repository = self._get_repository_by_name_and_owner(
            column_maker_repository_name, common.test_user_1_name
        )
        changeset_revision = self.get_repository_tip(column_maker_repository)
        strings_displayed = [
            "Tool dependencies",
            "emboss",
            "5.0.0",
            "package",
            "user1",
            changeset_revision,
            "Repository dependencies",
        ]
        self.display_manage_repository_page(repository, strings_displayed=strings_displayed)

    def test_0040_verify_repository_metadata(self):
        """Verify that resetting the metadata does not change it."""
        emboss_repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
        column_maker_repository = self._get_repository_by_name_and_owner(
            column_maker_repository_name, common.test_user_1_name
        )
        self.verify_unchanged_repository_metadata(emboss_repository)
        self.verify_unchanged_repository_metadata(column_maker_repository)
