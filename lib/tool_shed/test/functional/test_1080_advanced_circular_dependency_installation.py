import logging

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

log = logging.getLogger(__name__)

running_standalone = False


class TestRepositoryDependencies(ShedTwillTestCase):
    """Testing uninstalling and reinstalling repository dependencies, and setting tool panel sections."""

    requires_galaxy = True

    def test_0000_create_or_login_admin_user(self):
        """Create necessary user accounts and login as an admin user."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_and_populate_column_repository(self):
        """Create the category for this test suite, then create and populate column_maker."""
        category = self.create_category(name=category_name, description=category_description)
        global running_standalone
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name=column_repository_name,
            description=column_repository_description,
            long_description=column_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(repository):
            self.commit_tar_to_repository(
                repository,
                "column_maker/column_maker.tar",
                commit_message="Uploaded column_maker tarball.",
            )
            running_standalone = True

    def test_0010_create_and_populate_convert_repository(self):
        """Create and populate the convert_chars repository."""
        global running_standalone
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
        if self.repository_is_new(repository):
            self.commit_tar_to_repository(
                repository,
                "convert_chars/convert_chars.tar",
                commit_message="Uploaded convert_chars tarball.",
            )
            running_standalone = True

    def test_0015_upload_dependency_xml_if_needed(self):
        """If this test is being run by itself, it will not have repository dependencies configured yet."""
        global running_standalone
        if running_standalone:
            convert_repository = self._get_repository_by_name_and_owner(
                convert_repository_name, common.test_user_1_name
            )
            column_repository = self._get_repository_by_name_and_owner(column_repository_name, common.test_user_1_name)
            repository_dependencies_path = self.generate_temp_path("test_1080", additional_paths=["convert"])
            repository_tuple = (
                self.url,
                convert_repository.name,
                convert_repository.owner,
                self.get_repository_tip(convert_repository),
            )
            self.create_repository_dependency(
                repository=column_repository,
                repository_tuples=[repository_tuple],
                filepath=repository_dependencies_path,
            )
            repository_tuple = (
                self.url,
                column_repository.name,
                column_repository.owner,
                self.get_repository_tip(column_repository),
            )
            self.create_repository_dependency(
                repository=convert_repository,
                repository_tuples=[repository_tuple],
                filepath=repository_dependencies_path,
            )

    def test_0020_install_convert_repository(self):
        """Install convert_chars without repository dependencies into convert_chars tool panel section."""
        self._install_repository(
            convert_repository_name,
            common.test_user_1_name,
            category_name,
            install_tool_dependencies=False,
            install_repository_dependencies=False,
            new_tool_panel_section_label="convert_chars",
        )
        installed_convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        installed_column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        assert self._get_installed_repository_for(
            common.test_user_1, convert_repository_name, installed_convert_repository.installed_changeset_revision
        )
        if self.full_stack_galaxy:
            # This branch has been broken since we switched from mako to API for installing...
            self._assert_has_installed_repository_dependency(
                installed_convert_repository,
                column_repository_name,
                installed_column_repository.installed_changeset_revision,
            )
        else:
            # Previous mako had some string checks and such equivalent to this.
            self._assert_has_missing_dependency(installed_convert_repository, column_repository_name)

    def test_0025_install_column_repository(self):
        """Install column maker with repository dependencies into column_maker tool panel section."""
        self._install_repository(
            column_repository_name,
            common.test_user_1_name,
            category_name,
            install_repository_dependencies=True,
            new_tool_panel_section_label="column_maker",
        )
        installed_convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        installed_column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        assert self._get_installed_repository_for(
            common.test_user_1, "convert_chars_0080", installed_convert_repository.installed_changeset_revision
        )
        assert self._get_installed_repository_for(
            common.test_user_1, "column_maker_0080", installed_column_repository.installed_changeset_revision
        )
        self._assert_has_installed_repository_dependency(
            installed_column_repository, "convert_chars_0080", installed_convert_repository.installed_changeset_revision
        )

    def test_0030_deactivate_convert_repository(self):
        """Deactivate convert_chars, verify that column_maker is installed and missing repository dependencies."""
        installed_convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        installed_column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        self.deactivate_repository(installed_convert_repository)
        self._assert_has_missing_dependency(installed_column_repository, "convert_chars_0080")

    def test_0035_reactivate_convert_repository(self):
        """Reactivate convert_chars, both convert_chars and column_maker should now show as installed."""
        installed_convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        installed_column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        self.reactivate_repository(installed_convert_repository)
        self._assert_has_installed_repository_dependency(
            installed_column_repository, "convert_chars_0080", installed_convert_repository.installed_changeset_revision
        )

    def test_0040_deactivate_column_repository(self):
        """Deactivate column_maker, verify that convert_chars is installed and missing repository dependencies."""
        installed_convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        installed_column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        self.deactivate_repository(installed_column_repository)
        self._assert_has_missing_dependency(installed_convert_repository, "column_maker_0080")

    def test_0045_deactivate_convert_repository(self):
        """Deactivate convert_chars, verify that both convert_chars and column_maker are deactivated."""
        installed_convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        self.deactivate_repository(installed_convert_repository)
        self._assert_has_no_installed_repos_with_names("column_maker_0080", "convert_chars_0080")

    def test_0050_reactivate_column_repository(self):
        """Reactivate column_maker. This should not automatically reactivate convert_chars, so column_maker should be displayed as installed but missing repository dependencies."""
        installed_column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        self.reactivate_repository(installed_column_repository)
        self._assert_has_missing_dependency(installed_column_repository, "convert_chars_0080")

    def test_0055_reactivate_convert_repository(self):
        """Activate convert_chars. Both convert_chars and column_maker should now show as installed."""
        installed_convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        installed_column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        self.reactivate_repository(installed_convert_repository)
        self._assert_has_installed_repos_with_names("column_maker_0080", "convert_chars_0080")
        self._assert_is_not_missing_dependency(installed_column_repository, "convert_chars_0080")
        self._assert_is_not_missing_dependency(installed_convert_repository, "column_maker_0080")

    def test_0060_uninstall_column_repository(self):
        """Uninstall column_maker. Verify that convert_chars is installed and missing repository dependencies."""
        installed_convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        installed_column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        self._uninstall_repository(installed_column_repository)
        self._assert_has_missing_dependency(installed_convert_repository, "column_maker_0080")

    def test_0065_reinstall_column_repository(self):
        """Reinstall column_maker without repository dependencies, verify both convert_chars and column_maker are installed."""
        installed_convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        installed_column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        self.reinstall_repository_api(installed_column_repository, install_repository_dependencies=False)
        self._assert_has_installed_repos_with_names("column_maker_0080", "convert_chars_0080")
        self._assert_is_not_missing_dependency(installed_column_repository, "convert_chars_0080")
        self._assert_is_not_missing_dependency(installed_convert_repository, "column_maker_0080")

    def test_0070_uninstall_convert_repository(self):
        """Uninstall convert_chars, verify column_maker installed but missing repository dependencies."""
        installed_convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        installed_column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        self.deactivate_repository(installed_convert_repository)
        self._assert_has_missing_dependency(installed_column_repository, "convert_chars_0080")

    def test_0075_uninstall_column_repository(self):
        """Uninstall column_maker, verify that both convert_chars and column_maker are uninstalled."""
        installed_column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        self.deactivate_repository(installed_column_repository)
        self._assert_has_no_installed_repos_with_names("column_maker_0080", "convert_chars_0080")

    def test_0080_reinstall_convert_repository(self):
        """Reinstall convert_chars with repository dependencies, verify that this installs both convert_chars and column_maker."""
        installed_convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        installed_column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        self.reinstall_repository_api(installed_convert_repository, install_repository_dependencies=True)
        self._assert_has_installed_repos_with_names("column_maker_0080", "convert_chars_0080")
        self._assert_is_not_missing_dependency(installed_column_repository, "convert_chars_0080")
        self._assert_is_not_missing_dependency(installed_convert_repository, "column_maker_0080")
