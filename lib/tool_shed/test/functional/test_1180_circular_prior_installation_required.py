import logging

from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

log = logging.getLogger(__name__)

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
Create column_maker, filtering, and convert_chars.

Column maker repository dependency:
<repository toolshed="self.url" name="convert_chars" owner="test" changeset_revision="c3041382815c" prior_installation_required="True" />
<repository toolshed="self.url" name="filtering" owner="test" changeset_revision="c3041382815c" prior_installation_required="True" />

Convert chars repository dependency:
<repository toolshed="self.url" name="column_maker" owner="test" changeset_revision="c3041382815c" prior_installation_required="True" />
<repository toolshed="self.url" name="filtering" owner="test" changeset_revision="c3041382815c" prior_installation_required="True" />

Filtering repository dependency:
<repository toolshed="self.url" name="column_maker" owner="test" changeset_revision="c3041382815c" prior_installation_required="True" />
<repository toolshed="self.url" name="convert_chars" owner="test" changeset_revision="c3041382815c" prior_installation_required="True" />

Verify display.

Galaxy side:

Install filtering.
Verify that convert_chars was installed first, contrary to the ordering that would be present without prior_installation_required.
"""

running_standalone = False


class TestSimplePriorInstallation(ShedTwillTestCase):
    """Test features related to datatype converters."""

    requires_galaxy = True

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_convert_repository(self):
        """Create and populate convert_chars_0160."""
        global running_standalone
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
        if self.repository_is_new(repository):
            running_standalone = True
            self.commit_tar_to_repository(
                repository,
                "convert_chars/convert_chars.tar",
                commit_message="Uploaded convert_chars tarball.",
            )

    def test_0010_create_column_repository(self):
        """Create and populate convert_chars_0160."""
        category = self.create_category(name=category_name, description=category_description)
        repository = self.get_or_create_repository(
            name=column_repository_name,
            description=column_repository_description,
            long_description=column_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if running_standalone:
            self.commit_tar_to_repository(
                repository,
                "column_maker/column_maker.tar",
                commit_message="Uploaded column_maker tarball.",
            )

    def test_0015_create_filtering_repository(self):
        """Create and populate filtering_0160."""
        category = self.create_category(name=category_name, description=category_description)
        repository = self.get_or_create_repository(
            name=filter_repository_name,
            description=filter_repository_description,
            long_description=filter_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if running_standalone:
            self.commit_tar_to_repository(
                repository,
                "filtering/filtering_1.1.0.tar",
                commit_message="Uploaded filtering 1.1.0 tarball.",
            )

    def test_0020_create_repository_dependency(self):
        """Create a repository dependency specifying convert_chars.

        Each of the three repositories should depend on the other two, to make this as circular as possible.
        """
        filter_repository = self._get_repository_by_name_and_owner(filter_repository_name, common.test_user_1_name)
        column_repository = self._get_repository_by_name_and_owner(column_repository_name, common.test_user_1_name)
        convert_repository = self._get_repository_by_name_and_owner(convert_repository_name, common.test_user_1_name)
        filter_revision = self.get_repository_tip(filter_repository)
        column_revision = self.get_repository_tip(column_repository)
        convert_revision = self.get_repository_tip(convert_repository)
        if running_standalone:
            dependency_xml_path = self.generate_temp_path("test_1160", additional_paths=["column"])
            column_tuple = (self.url, column_repository.name, column_repository.owner, column_revision)
            convert_tuple = (self.url, convert_repository.name, convert_repository.owner, convert_revision)
            filter_tuple = (self.url, filter_repository.name, filter_repository.owner, filter_revision)
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
        filter_repository = self._get_repository_by_name_and_owner(filter_repository_name, common.test_user_1_name)
        column_repository = self._get_repository_by_name_and_owner(column_repository_name, common.test_user_1_name)
        convert_repository = self._get_repository_by_name_and_owner(convert_repository_name, common.test_user_1_name)
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

    def test_0030_install_filtering_repository(self):
        """Install the filtering_0160 repository."""
        filter_repository = self._get_repository_by_name_and_owner(filter_repository_name, common.test_user_1_name)
        preview_strings_displayed = ["filtering_0160", self.get_repository_tip(filter_repository)]
        self._install_repository(
            filter_repository_name,
            common.test_user_1_name,
            category_name,
            install_tool_dependencies=False,
            install_repository_dependencies=True,
            preview_strings_displayed=preview_strings_displayed,
        )

    def test_0035_verify_installation_order(self):
        """Verify that convert_chars_0160 and column_maker_0160 were installed before filtering_0160."""
        filter_repository = self._get_installed_repository_by_name_owner(
            filter_repository_name, common.test_user_1_name
        )
        column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        # Filtering was selected for installation, so convert chars and column maker should have been installed first.
        assert (
            filter_repository.update_time > convert_repository.update_time
        ), "Error: convert_chars_0160 shows a later update time than filtering_0160"
        assert (
            filter_repository.update_time > column_repository.update_time
        ), "Error: column_maker_0160 shows a later update time than filtering_0160"

    def test_0040_deactivate_all_repositories(self):
        """Uninstall convert_chars_0160, column_maker_0160, and filtering_0160."""
        filter_repository = self._get_installed_repository_by_name_owner(
            filter_repository_name, common.test_user_1_name
        )
        column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        self.deactivate_repository(filter_repository)
        self.deactivate_repository(column_repository)
        self.deactivate_repository(convert_repository)

    def test_0045_reactivate_filter_repository(self):
        """Reinstall the filtering_0160 repository."""
        filter_repository = self._get_installed_repository_by_name_owner(
            filter_repository_name, common.test_user_1_name
        )
        self.reactivate_repository(filter_repository)
        self._assert_has_installed_repos_with_names("filtering_0160")
        self._assert_has_valid_tool_with_name("Filter1")
        self._assert_repo_has_tool_with_id(filter_repository, "Filter1")

    def test_0050_verify_reinstallation_order(self):
        """Verify that convert_chars_0160 and column_maker_0160 were reinstalled before filtering_0160."""
        # Fixme: this test is not covering any important behavior since repositories were only deactivated and not uninstalled.
        filter_repository = self._get_installed_repository_by_name_owner(
            filter_repository_name, common.test_user_1_name
        )
        column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        # Filtering was selected for reinstallation, so convert chars and column maker should have been installed first.
        if self.full_stack_galaxy:
            for repo in [convert_repository, column_repository, filter_repository]:
                self.test_db_util.install_session().refresh(repo)
        assert (
            filter_repository.update_time > convert_repository.update_time
        ), "Prior installed convert_chars_0160 shows a later update time than filtering_0160"
        assert (
            filter_repository.update_time > column_repository.update_time
        ), "Prior installed column_maker_0160 shows a later update time than filtering_0160"
