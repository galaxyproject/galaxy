from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

freebayes_repository_name = "freebayes_0040"
freebayes_repository_description = "Galaxy's freebayes tool for test 0040"
freebayes_repository_long_description = "Long description of Galaxy's freebayes tool for test 0040"

filtering_repository_name = "filtering_0040"
filtering_repository_description = "Galaxy's filtering tool for test 0040"
filtering_repository_long_description = "Long description of Galaxy's filtering tool for test 0040"

category_name = "test_0040_repository_circular_dependencies"

running_standalone = False


class TestInstallingCircularDependencies(ShedTwillTestCase):
    """Verify that the code correctly handles installing repositories with circular dependencies."""

    requires_galaxy = True

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_freebayes_repository(self):
        """Create and populate freebayes_0040."""
        global running_standalone
        category = self.create_category(
            name=category_name, description="Testing handling of circular repository dependencies."
        )
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name=freebayes_repository_name,
            description=freebayes_repository_description,
            long_description=freebayes_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(repository):
            running_standalone = True
            self.commit_tar_to_repository(
                repository,
                "freebayes/freebayes.tar",
                commit_message="Uploaded the tool tarball.",
            )

    def test_0015_create_filtering_repository(self):
        """Create and populate filtering_0040."""
        global running_standalone
        category = self.create_category(
            name=category_name, description="Testing handling of circular repository dependencies."
        )
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name=filtering_repository_name,
            description=filtering_repository_description,
            long_description=filtering_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(repository):
            running_standalone = True
            self.commit_tar_to_repository(
                repository,
                "filtering/filtering_1.1.0.tar",
                commit_message="Uploaded the tool tarball for filtering 1.1.0.",
            )

    def test_0020_create_repository_dependencies(self):
        """Set up the filtering and freebayes repository dependencies."""
        # The dependency structure should look like:
        # Filtering revision 0 -> freebayes revision 0.
        # Freebayes revision 0 -> filtering revision 1.
        # Filtering will have two revisions, one with just the filtering tool, and one with the filtering tool and a dependency on freebayes.
        if running_standalone:
            freebayes_repository = self._get_repository_by_name_and_owner(
                freebayes_repository_name, common.test_user_1_name
            )
            filtering_repository = self._get_repository_by_name_and_owner(
                filtering_repository_name, common.test_user_1_name
            )
            repository_dependencies_path = self.generate_temp_path("test_1040", additional_paths=["circular"])
            repository_tuple = (
                self.url,
                freebayes_repository.name,
                freebayes_repository.owner,
                self.get_repository_tip(freebayes_repository),
            )
            self.create_repository_dependency(
                repository=filtering_repository,
                repository_tuples=[repository_tuple],
                filepath=repository_dependencies_path,
            )
            repository_tuple = (
                self.url,
                filtering_repository.name,
                filtering_repository.owner,
                self.get_repository_tip(filtering_repository),
            )
            self.create_repository_dependency(
                repository=freebayes_repository,
                repository_tuples=[repository_tuple],
                filepath=repository_dependencies_path,
            )

    def test_0025_install_freebayes_repository(self):
        """Install freebayes with blank tool panel section, without tool dependencies but with repository dependencies."""
        self._install_repository(
            freebayes_repository_name,
            common.test_user_1_name,
            category_name,
            install_tool_dependencies=False,
            install_repository_dependencies=True,
        )

    def test_0030_uninstall_filtering_repository(self):
        """Deactivate filtering, verify tool panel section and missing repository dependency."""
        installed_freebayes_repository = self._get_installed_repository_by_name_owner(
            freebayes_repository_name, common.test_user_1_name
        )
        installed_filtering_repository = self._get_installed_repository_by_name_owner(
            filtering_repository_name, common.test_user_1_name
        )
        assert self._get_installed_repository_for(
            common.test_user_1, freebayes_repository_name, installed_freebayes_repository.installed_changeset_revision
        )
        assert self._get_installed_repository_for(
            common.test_user_1, filtering_repository_name, installed_filtering_repository.installed_changeset_revision
        )
        self.deactivate_repository(installed_filtering_repository)
        self._refresh_tool_shed_repository(installed_filtering_repository)
        self._assert_has_missing_dependency(installed_freebayes_repository, filtering_repository_name)
        self.check_galaxy_repository_db_status(filtering_repository_name, common.test_user_1_name, "Deactivated")

    def test_0035_reactivate_filtering_repository(self):
        """Reinstall filtering into 'filtering' tool panel section."""
        installed_filtering_repository = self._get_installed_repository_by_name_owner(
            freebayes_repository_name, common.test_user_1_name
        )
        self.reinstall_repository_api(
            installed_filtering_repository,
            install_tool_dependencies=False,
            install_repository_dependencies=True,
            new_tool_panel_section_label="filtering",
        )
        installed_freebayes_repository = self._get_installed_repository_by_name_owner(
            freebayes_repository_name, common.test_user_1_name
        )
        self._assert_is_not_missing_dependency(installed_freebayes_repository, filtering_repository_name)

    def test_0040_uninstall_freebayes_repository(self):
        """Deactivate freebayes, verify tool panel section and missing repository dependency."""
        installed_freebayes_repository = self._get_installed_repository_by_name_owner(
            freebayes_repository_name, common.test_user_1_name
        )
        installed_filtering_repository = self._get_installed_repository_by_name_owner(
            filtering_repository_name, common.test_user_1_name
        )
        assert self._get_installed_repository_for(
            common.test_user_1, freebayes_repository_name, installed_freebayes_repository.installed_changeset_revision
        )
        assert self._get_installed_repository_for(
            common.test_user_1, filtering_repository_name, installed_filtering_repository.installed_changeset_revision
        )
        self.deactivate_repository(installed_freebayes_repository)
        assert not self._get_installed_repository_for(
            common.test_user_1, freebayes_repository_name, installed_freebayes_repository.installed_changeset_revision
        )
        self._refresh_tool_shed_repository(installed_filtering_repository)
        self._assert_has_missing_dependency(installed_filtering_repository, freebayes_repository_name)
        self.check_galaxy_repository_db_status("freebayes_0040", "user1", "Deactivated")

    def test_0045_deactivate_filtering_repository(self):
        """Deactivate filtering, verify tool panel section."""
        installed_filtering_repository = self._get_installed_repository_by_name_owner(
            filtering_repository_name, common.test_user_1_name
        )
        installed_freebayes_repository = self._get_installed_repository_by_name_owner(
            freebayes_repository_name, common.test_user_1_name
        )
        assert self._get_installed_repository_for(
            common.test_user_1, filtering_repository_name, installed_filtering_repository.installed_changeset_revision
        )
        self.deactivate_repository(installed_filtering_repository)
        assert not self._get_installed_repository_for(
            common.test_user_1, freebayes_repository_name, installed_freebayes_repository.installed_changeset_revision
        )
        assert not self._get_installed_repository_for(
            common.test_user_1, filtering_repository_name, installed_filtering_repository.installed_changeset_revision
        )
        self._refresh_tool_shed_repository(installed_freebayes_repository)
        self._assert_has_missing_dependency(installed_freebayes_repository, filtering_repository_name)
        self.check_galaxy_repository_db_status(filtering_repository_name, common.test_user_1_name, "Deactivated")
