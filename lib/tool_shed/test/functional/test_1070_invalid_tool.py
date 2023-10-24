from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

repository_name = "bismark_0070"
repository_description = "Galaxy's bismark wrapper"
repository_long_description = "Long description of Galaxy's bismark wrapper"
category_name = "Test 0070 Invalid Tool Revisions"
category_description = "Test 1070 for a repository with an invalid tool."


class TestFreebayesRepository(ShedTwillTestCase):
    """Test repository with multiple revisions with invalid tools."""

    requires_galaxy = True

    def test_0000_create_or_login_admin_user(self):
        """Create necessary user accounts and login as an admin user."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_ensure_existence_of_repository_and_category(self):
        """Create freebayes repository and upload only freebayes.xml. This should result in an error message and invalid tool."""
        self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        category = self.populator.get_category_with_name(category_name)
        repository = self.get_or_create_repository(
            name=repository_name,
            description=repository_description,
            long_description=repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(repository):
            self.user_populator().setup_bismark_repo(repository)

    def test_0010_browse_tool_shed(self):
        """Browse the available tool sheds in this Galaxy instance and preview the bismark repository."""
        self.browse_tool_shed(url=self.url, strings_displayed=[category_name])
        category = self.populator.get_category_with_name(category_name)
        self.browse_category(category, strings_displayed=[repository_name])
        self.preview_repository_in_tool_shed(
            repository_name, common.test_user_1_name, strings_displayed=[repository_name]
        )

    def test_0015_install_freebayes_repository(self):
        """Install the test repository without installing tool dependencies."""
        self._install_repository(
            repository_name,
            common.test_user_1_name,
            category_name,
            install_tool_dependencies=False,
            new_tool_panel_section_label="test_1070",
        )
        installed_repository = self._get_installed_repository_by_name_owner(repository_name, common.test_user_1_name)
        assert self._get_installed_repository_for(
            common.test_user_1, repository_name, installed_repository.installed_changeset_revision
        )
        self.update_installed_repository(installed_repository, verify_no_updates=True)
        self._assert_repo_has_invalid_tool_in_file(installed_repository, "bismark_bowtie_wrapper.xml")
