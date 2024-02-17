import logging

from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

column_repository_name = "column_maker_1085"
column_repository_description = "Add column"
column_repository_long_description = "Compute an expression on every row"

convert_repository_name = "convert_chars_1085"
convert_repository_description = "Convert delimiters"
convert_repository_long_description = "Convert delimiters to tab"

category_name = "Test 1085 Advanced Circular Dependencies"
category_description = "Test circular dependency features"

log = logging.getLogger(__name__)


class TestRepositoryDependencies(ShedTwillTestCase):
    """Testing the behavior of repository dependencies with tool panel sections."""

    requires_galaxy = True

    def test_0000_create_or_login_admin_user(self):
        """Create necessary user accounts and login as an admin user."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_and_populate_column_repository(self):
        """Create a category for this test suite and add repositories to it."""
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
        if self.repository_is_new(repository):
            self.commit_tar_to_repository(
                repository,
                "column_maker/column_maker.tar",
                commit_message="Uploaded column_maker tarball.",
            )

    def test_0010_create_and_populate_convert_repository(self):
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

    def test_0015_create_and_upload_dependency_files(self):
        convert_repository = self._get_repository_by_name_and_owner(convert_repository_name, common.test_user_1_name)
        column_repository = self._get_repository_by_name_and_owner(column_repository_name, common.test_user_1_name)
        repository_dependencies_path = self.generate_temp_path("test_1085", additional_paths=["column"])
        repository_tuple = (
            self.url,
            convert_repository.name,
            convert_repository.owner,
            self.get_repository_tip(convert_repository),
        )
        self.create_repository_dependency(
            repository=column_repository, repository_tuples=[repository_tuple], filepath=repository_dependencies_path
        )
        repository_tuple = (
            self.url,
            column_repository.name,
            column_repository.owner,
            self.get_repository_tip(column_repository),
        )
        self.create_repository_dependency(
            repository=convert_repository, repository_tuples=[repository_tuple], filepath=repository_dependencies_path
        )

    def test_0020_install_repositories(self):
        """Install column_maker into column_maker tool panel section and install repository dependencies."""
        self._install_repository(
            column_repository_name,
            common.test_user_1_name,
            category_name,
            install_tool_dependencies=False,
            install_repository_dependencies=True,
            new_tool_panel_section_label="column_maker",
        )
        installed_convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        self._refresh_tool_shed_repository(installed_convert_repository)
        self._assert_has_installed_repos_with_names("convert_chars_1085", "column_maker_1085")
        self._assert_is_not_missing_dependency(installed_convert_repository, "column_maker_1085")

    def test_0025_uninstall_column_repository(self):
        """uninstall column_maker, verify same section"""
        installed_column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        self._uninstall_repository(installed_column_repository)
        self.check_galaxy_repository_tool_panel_section(installed_column_repository, "column_maker")

    def test_0030_uninstall_convert_repository(self):
        installed_convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        self._uninstall_repository(installed_convert_repository)
        self._refresh_tool_shed_repository(installed_convert_repository)
        self.check_galaxy_repository_tool_panel_section(installed_convert_repository, "column_maker")

    def test_0035_reinstall_column_repository(self):
        """reinstall column_maker into new section 'new_column_maker' (no_changes = false), no dependencies"""
        installed_column_repository = self._get_installed_repository_by_name_owner(
            column_repository_name, common.test_user_1_name
        )
        self.reinstall_repository_api(
            installed_column_repository,
            install_tool_dependencies=False,
            install_repository_dependencies=False,
            new_tool_panel_section_label="new_column_maker",
        )
        self._assert_has_installed_repos_with_names("column_maker_1085")

    def test_0040_reinstall_convert_repository(self):
        """reinstall convert_chars into new section 'new_convert_chars' (no_changes = false), no dependencies"""
        installed_convert_repository = self._get_installed_repository_by_name_owner(
            convert_repository_name, common.test_user_1_name
        )
        self.reinstall_repository_api(
            installed_convert_repository,
            install_tool_dependencies=False,
            install_repository_dependencies=False,
            new_tool_panel_section_label="new_convert_chars",
        )
        self._assert_has_installed_repos_with_names("convert_chars_1085")

    # The following check fails somewhere around 5% of the time maybe on Jenkins.
    # https://jenkins.galaxyproject.org/job/docker-toolshed/5578/
    # https://jenkins.galaxyproject.org/job/docker-toolshed/5198/
    # def test_0045_uninstall_and_verify_tool_panel_sections( self ):
    #    '''uninstall both and verify tool panel sections'''
    #    installed_convert_repository = self._get_installed_repository_by_name_owner( convert_repository_name,
    #                                                                                        common.test_user_1_name )
    #    installed_column_repository = self._get_installed_repository_by_name_owner( column_repository_name,
    #                                                                                        common.test_user_1_name )
    #    self._uninstall_repository( installed_convert_repository )
    #    self._uninstall_repository( installed_column_repository )
    #    self.test_db_util.ga_refresh( installed_convert_repository )
    #    self.test_db_util.ga_refresh( installed_column_repository )
    #    self.check_galaxy_repository_tool_panel_section( installed_column_repository, 'new_column_maker' )
    #    self.check_galaxy_repository_tool_panel_section( installed_convert_repository, 'new_convert_chars' )
