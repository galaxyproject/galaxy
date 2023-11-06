from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

column_repository_name = "column_maker_0080"
column_repository_description = "Add column"
column_repository_long_description = "Compute an expression on every row"

convert_repository_name = "convert_chars_0080"
convert_repository_description = "Convert delimiters"
convert_repository_long_description = "Convert delimiters to tab"

category_name = "Test 0080 Advanced Circular Dependencies"
category_description = "Test circular dependency features"


class TestRepositoryCircularDependencies(ShedTwillTestCase):
    """Verify that the code correctly handles circular dependencies."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_column_repository(self):
        """Create and populate the column_maker repository."""
        category = self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name=column_repository_name,
            description=column_repository_description,
            long_description=column_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        self.commit_tar_to_repository(
            repository,
            "column_maker/column_maker.tar",
            commit_message="Uploaded column_maker tarball.",
        )

    def test_0005_create_convert_repository(self):
        """Create and populate the convert_chars repository."""
        self.login(email=common.admin_email, username=common.admin_username)
        category = self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name=convert_repository_name,
            description=convert_repository_description,
            long_description=convert_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        self.commit_tar_to_repository(
            repository,
            "convert_chars/convert_chars.tar",
            commit_message="Uploaded convert_chars tarball.",
        )

    def test_0020_create_repository_dependencies(self):
        """Upload a repository_dependencies.xml file that specifies the current revision of convert_chars_0080 to the column_maker_0080 repository."""
        convert_repository = self._get_repository_by_name_and_owner(convert_repository_name, common.test_user_1_name)
        column_repository = self._get_repository_by_name_and_owner(column_repository_name, common.test_user_1_name)
        repository_dependencies_path = self.generate_temp_path("test_0080", additional_paths=["convert"])
        repository_tuple = (
            self.url,
            convert_repository.name,
            convert_repository.owner,
            self.get_repository_tip(convert_repository),
        )
        self.create_repository_dependency(
            repository=column_repository, repository_tuples=[repository_tuple], filepath=repository_dependencies_path
        )

    def test_0025_create_dependency_on_filtering(self):
        """Upload a repository_dependencies.xml file that specifies the current revision of filtering to the freebayes_0040 repository."""
        convert_repository = self._get_repository_by_name_and_owner(convert_repository_name, common.test_user_1_name)
        column_repository = self._get_repository_by_name_and_owner(column_repository_name, common.test_user_1_name)
        repository_dependencies_path = self.generate_temp_path("test_0080", additional_paths=["convert"])
        repository_tuple = (
            self.url,
            column_repository.name,
            column_repository.owner,
            self.get_repository_tip(column_repository),
        )
        self.create_repository_dependency(
            repository=convert_repository, repository_tuples=[repository_tuple], filepath=repository_dependencies_path
        )

    def test_0030_verify_repository_dependencies(self):
        """Verify that each repository can depend on the other without causing an infinite loop."""
        convert_repository = self._get_repository_by_name_and_owner(convert_repository_name, common.test_user_1_name)
        column_repository = self._get_repository_by_name_and_owner(column_repository_name, common.test_user_1_name)
        self.check_repository_dependency(
            convert_repository, column_repository, self.get_repository_tip(column_repository)
        )
        self.check_repository_dependency(
            column_repository, convert_repository, self.get_repository_tip(convert_repository)
        )

    def test_0035_verify_repository_metadata(self):
        """Verify that resetting the metadata does not change it."""
        column_repository = self._get_repository_by_name_and_owner(column_repository_name, common.test_user_1_name)
        convert_repository = self._get_repository_by_name_and_owner(convert_repository_name, common.test_user_1_name)
        for repository in [column_repository, convert_repository]:
            self.verify_unchanged_repository_metadata(repository)
