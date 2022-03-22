from ..base.twilltestcase import (
    common,
    ShedTwillTestCase,
)

filter_repository_name = "filtering_0160"
filter_repository_description = "Galaxy's filtering tool for test 0160"
filter_repository_long_description = "Long description of Galaxy's filtering tool for test 0160"

column_repository_name = "column_maker_0160"
column_repository_description = "Add column"
column_repository_long_description = "Compute an expression on every row"

convert_repository_name = "convert_chars_0160"
convert_repository_description = "Convert delimiters"
convert_repository_long_description = "Convert delimiters to tab"

category_name = "Test 0160 Simple Prior Installation"
category_description = "Test 0160 Simple Prior Installation"

"""
Create column_maker and convert_chars.

Column maker repository dependency:
<repository toolshed="self.url" name="convert_chars" owner="test" changeset_revision="c3041382815c" prior_installation_required="True" />

Verify display.
"""


class TestSimplePriorInstallation(ShedTwillTestCase):
    """Test features related to datatype converters."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        test_user_1 = self.test_db_util.get_user(common.test_user_1_email)
        assert (
            test_user_1 is not None
        ), f"Problem retrieving user with email {common.test_user_1_email} from the database"
        self.test_db_util.get_private_role(test_user_1)
        self.login(email=common.admin_email, username=common.admin_username)
        admin_user = self.test_db_util.get_user(common.admin_email)
        assert admin_user is not None, f"Problem retrieving user with email {common.admin_email} from the database"
        self.test_db_util.get_private_role(admin_user)

    def test_0005_create_convert_repository(self):
        """Create and populate convert_chars_0160."""
        category = self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name=convert_repository_name,
            description=convert_repository_description,
            long_description=convert_repository_long_description,
            owner=common.test_user_1_name,
            category_id=self.security.encode_id(category.id),
            strings_displayed=[],
        )
        self.upload_file(
            repository,
            filename="convert_chars/convert_chars.tar",
            filepath=None,
            valid_tools_only=True,
            uncompress_file=True,
            remove_repo_files_not_in_tar=False,
            commit_message="Uploaded convert_chars tarball.",
            strings_displayed=[],
            strings_not_displayed=[],
        )

    def test_0010_create_column_repository(self):
        """Create and populate convert_chars_0160."""
        category = self.create_category(name=category_name, description=category_description)
        repository = self.get_or_create_repository(
            name=column_repository_name,
            description=column_repository_description,
            long_description=column_repository_long_description,
            owner=common.test_user_1_name,
            category_id=self.security.encode_id(category.id),
            strings_displayed=[],
        )
        self.upload_file(
            repository,
            filename="column_maker/column_maker.tar",
            filepath=None,
            valid_tools_only=True,
            uncompress_file=True,
            remove_repo_files_not_in_tar=False,
            commit_message="Uploaded column_maker tarball.",
            strings_displayed=[],
            strings_not_displayed=[],
        )

    def test_0015_create_filtering_repository(self):
        """Create and populate filtering_0160."""
        category = self.create_category(name=category_name, description=category_description)
        repository = self.get_or_create_repository(
            name=filter_repository_name,
            description=filter_repository_description,
            long_description=filter_repository_long_description,
            owner=common.test_user_1_name,
            category_id=self.security.encode_id(category.id),
            strings_displayed=[],
        )
        self.upload_file(
            repository,
            filename="filtering/filtering_1.1.0.tar",
            filepath=None,
            valid_tools_only=True,
            uncompress_file=True,
            remove_repo_files_not_in_tar=False,
            commit_message="Uploaded filtering 1.1.0 tarball.",
            strings_displayed=[],
            strings_not_displayed=[],
        )

    def test_0020_create_repository_dependency(self):
        """Create a repository dependency specifying convert_chars.

        Each of the three repositories should depend on the other two, to make this as circular as possible.
        """
        filter_repository = self.test_db_util.get_repository_by_name_and_owner(
            filter_repository_name, common.test_user_1_name
        )
        column_repository = self.test_db_util.get_repository_by_name_and_owner(
            column_repository_name, common.test_user_1_name
        )
        convert_repository = self.test_db_util.get_repository_by_name_and_owner(
            convert_repository_name, common.test_user_1_name
        )
        dependency_xml_path = self.generate_temp_path("test_0160", additional_paths=["column"])
        filter_revision = self.get_repository_tip(filter_repository)
        column_revision = self.get_repository_tip(column_repository)
        convert_revision = self.get_repository_tip(convert_repository)
        column_tuple = (self.url, column_repository.name, column_repository.user.username, column_revision)
        convert_tuple = (self.url, convert_repository.name, convert_repository.user.username, convert_revision)
        filter_tuple = (self.url, filter_repository.name, filter_repository.user.username, filter_revision)
        self.create_repository_dependency(
            repository=column_repository,
            repository_tuples=[convert_tuple, filter_tuple],
            filepath=dependency_xml_path,
            prior_installation_required=False,
        )
        self.create_repository_dependency(
            repository=convert_repository,
            repository_tuples=[column_tuple, filter_tuple],
            filepath=dependency_xml_path,
            prior_installation_required=False,
        )
        self.create_repository_dependency(
            repository=filter_repository,
            repository_tuples=[convert_tuple, column_tuple],
            filepath=dependency_xml_path,
            prior_installation_required=True,
        )

    def test_0025_verify_repository_dependency(self):
        """Verify that the previously generated repositiory dependency displays correctly."""
        filter_repository = self.test_db_util.get_repository_by_name_and_owner(
            filter_repository_name, common.test_user_1_name
        )
        column_repository = self.test_db_util.get_repository_by_name_and_owner(
            column_repository_name, common.test_user_1_name
        )
        convert_repository = self.test_db_util.get_repository_by_name_and_owner(
            convert_repository_name, common.test_user_1_name
        )
        self.check_repository_dependency(
            repository=column_repository,
            depends_on_repository=convert_repository,
            depends_on_changeset_revision=None,
            changeset_revision=None,
        )
        self.check_repository_dependency(
            repository=column_repository,
            depends_on_repository=filter_repository,
            depends_on_changeset_revision=None,
            changeset_revision=None,
        )
        self.check_repository_dependency(
            repository=convert_repository,
            depends_on_repository=column_repository,
            depends_on_changeset_revision=None,
            changeset_revision=None,
        )
        self.check_repository_dependency(
            repository=convert_repository,
            depends_on_repository=filter_repository,
            depends_on_changeset_revision=None,
            changeset_revision=None,
        )
        self.check_repository_dependency(
            repository=filter_repository,
            depends_on_repository=column_repository,
            depends_on_changeset_revision=None,
            changeset_revision=None,
        )
        self.check_repository_dependency(
            repository=filter_repository,
            depends_on_repository=convert_repository,
            depends_on_changeset_revision=None,
            changeset_revision=None,
        )
