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
emboss_repository_description = "Galaxy wrappers for Emboss version 5.0.0 tools for test 0030"
emboss_repository_long_description = "Galaxy wrappers for Emboss version 5.0.0 tools for test 0030"


class TestRepositoryDependencyRevisions(ShedTwillTestCase):
    """Test dependencies on different revisions of a repository."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_category(self):
        """Create a category for this test suite"""
        self.create_category(
            name="Test 0030 Repository Dependency Revisions", description="Testing repository dependencies by revision."
        )

    def test_0010_create_emboss_5_repository(self):
        """Create and populate the emboss_5_0030 repository."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        category = self.populator.get_category_with_name("Test 0030 Repository Dependency Revisions")
        repository = self.get_or_create_repository(
            name=emboss_5_repository_name,
            description=emboss_repository_description,
            long_description=emboss_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
        )
        self.upload_file(
            repository,
            filename="emboss/emboss.tar",
            filepath=None,
            valid_tools_only=True,
            uncompress_file=False,
            remove_repo_files_not_in_tar=False,
            commit_message="Uploaded tool tarball.",
            strings_displayed=[],
            strings_not_displayed=[],
        )

    def test_0015_create_emboss_6_repository(self):
        """Create and populate the emboss_6_0030 repository."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        category = self.populator.get_category_with_name("Test 0030 Repository Dependency Revisions")
        repository = self.get_or_create_repository(
            name=emboss_6_repository_name,
            description=emboss_repository_description,
            long_description=emboss_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
        )
        self.upload_file(
            repository,
            filename="emboss/emboss.tar",
            filepath=None,
            valid_tools_only=True,
            uncompress_file=False,
            remove_repo_files_not_in_tar=False,
            commit_message="Uploaded tool tarball.",
            strings_displayed=[],
            strings_not_displayed=[],
        )

    def test_0020_create_dependent_repository(self):
        """Create and populate the emboss_datatypes_0030 repository."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        category = self.populator.get_category_with_name("Test 0030 Repository Dependency Revisions")
        repository = self.get_or_create_repository(
            name=column_maker_repository_name,
            description=column_maker_repository_description,
            long_description=column_maker_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
        )
        if self.repository_is_new(repository):
            self.upload_file(
                repository,
                filename="column_maker/column_maker.tar",
                filepath=None,
                valid_tools_only=False,
                uncompress_file=True,
                remove_repo_files_not_in_tar=False,
                commit_message="Uploaded bismark tarball.",
                strings_displayed=[],
                strings_not_displayed=[],
            )

    def test_0025_create_emboss_repository(self):
        """Create and populate the emboss_0030 repository."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        category = self.populator.get_category_with_name("Test 0030 Repository Dependency Revisions")
        repository = self.get_or_create_repository(
            name=emboss_repository_name,
            description=emboss_repository_description,
            long_description=emboss_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
        )
        self.upload_file(
            repository,
            filename="emboss/emboss.tar",
            filepath=None,
            valid_tools_only=True,
            uncompress_file=False,
            remove_repo_files_not_in_tar=False,
            commit_message="Uploaded the tool tarball.",
            strings_displayed=[],
            strings_not_displayed=[],
        )

    def test_0030_generate_repository_dependencies_for_emboss_5(self):
        """Generate a repository_dependencies.xml file specifying emboss_datatypes and upload it to the emboss_5 repository."""
        column_maker_repository = self._get_repository_by_name_and_owner(
            column_maker_repository_name, common.test_user_1_name
        )
        emboss_5_repository = self._get_repository_by_name_and_owner(emboss_5_repository_name, common.test_user_1_name)
        repository_dependencies_path = self.generate_temp_path("test_0030", additional_paths=["emboss5"])
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

    def test_0035_generate_repository_dependencies_for_emboss_6(self):
        """Generate a repository_dependencies.xml file specifying emboss_datatypes and upload it to the emboss_6 repository."""
        emboss_6_repository = self._get_repository_by_name_and_owner(emboss_6_repository_name, common.test_user_1_name)
        column_maker_repository = self._get_repository_by_name_and_owner(
            column_maker_repository_name, common.test_user_1_name
        )
        repository_dependencies_path = self.generate_temp_path("test_0030", additional_paths=["emboss6"])
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

    def test_0040_generate_repository_dependency_on_emboss_5(self):
        """Create and upload repository_dependencies.xml for the emboss_5_0030 repository."""
        emboss_repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
        emboss_5_repository = self._get_repository_by_name_and_owner(emboss_5_repository_name, common.test_user_1_name)
        repository_dependencies_path = self.generate_temp_path("test_0030", additional_paths=["emboss", "5"])
        emboss_tuple = (
            self.url,
            emboss_5_repository.name,
            emboss_5_repository.owner,
            self.get_repository_tip(emboss_5_repository),
        )
        self.create_repository_dependency(
            repository=emboss_repository, repository_tuples=[emboss_tuple], filepath=repository_dependencies_path
        )

    def test_0045_generate_repository_dependency_on_emboss_6(self):
        """Create and upload repository_dependencies.xml for the emboss_6_0030 repository."""
        emboss_repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
        emboss_6_repository = self._get_repository_by_name_and_owner(emboss_6_repository_name, common.test_user_1_name)
        repository_dependencies_path = self.generate_temp_path("test_0030", additional_paths=["emboss", "5"])
        emboss_tuple = (
            self.url,
            emboss_6_repository.name,
            emboss_6_repository.owner,
            self.get_repository_tip(emboss_6_repository),
        )
        self.create_repository_dependency(
            repository=emboss_repository, repository_tuples=[emboss_tuple], filepath=repository_dependencies_path
        )

    def test_0050_verify_repository_dependency_revisions(self):
        """Verify that different metadata revisions of the emboss repository have different repository dependencies."""
        repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
        repository_metadata = [
            (metadata.metadata, metadata.changeset_revision) for metadata in self.get_repository_metadata(repository)
        ]
        column_maker_repository = self._get_repository_by_name_and_owner(
            column_maker_repository_name, common.test_user_1_name
        )
        column_maker_tip = self.get_repository_tip(column_maker_repository)
        strings_displayed = []
        # Iterate through all metadata revisions and check for repository dependencies.
        for _metadata, changeset_revision in repository_metadata:
            # Add the dependency description and bismark repository details to the strings to check.
            strings_displayed = ["column_maker_0030", "user1", column_maker_tip]
            strings_displayed.extend(["Tool dependencies", "emboss", "5.0.0", "package"])
            self.display_manage_repository_page(
                repository, changeset_revision=changeset_revision, strings_displayed=strings_displayed
            )

    def test_0055_verify_repository_metadata(self):
        """Verify that resetting the metadata does not change it."""
        emboss_repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
        emboss_5_repository = self._get_repository_by_name_and_owner(emboss_5_repository_name, common.test_user_1_name)
        emboss_6_repository = self._get_repository_by_name_and_owner(emboss_6_repository_name, common.test_user_1_name)
        column_maker_repository = self._get_repository_by_name_and_owner(
            column_maker_repository_name, common.test_user_1_name
        )
        for repository in [emboss_repository, emboss_5_repository, emboss_6_repository, column_maker_repository]:
            self.verify_unchanged_repository_metadata(repository)
