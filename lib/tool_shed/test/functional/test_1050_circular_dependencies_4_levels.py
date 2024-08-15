from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

emboss_repository_name = "emboss_0050"
emboss_repository_description = "Galaxy's emboss tool"
emboss_repository_long_description = "Long description of Galaxy's emboss tool"

filtering_repository_name = "filtering_0050"
filtering_repository_description = "Galaxy's filtering tool"
filtering_repository_long_description = "Long description of Galaxy's filtering tool"

freebayes_repository_name = "freebayes_0050"
freebayes_repository_description = "Galaxy's freebayes tool"
freebayes_repository_long_description = "Long description of Galaxy's freebayes tool"

column_repository_name = "column_maker_0050"
column_repository_description = "Add column"
column_repository_long_description = "Compute an expression on every row"

convert_repository_name = "convert_chars_0050"
convert_repository_description = "Convert delimiters"
convert_repository_long_description = "Convert delimiters to tab"

bismark_repository_name = "bismark_0050"
bismark_repository_description = "A flexible aligner."
bismark_repository_long_description = "A flexible aligner and methylation caller for Bisulfite-Seq applications."

category_name = "Test 0050 Circular Dependencies 5 Levels"
category_description = "Test circular dependency features"

running_standalone = False


class TestInstallRepositoryCircularDependencies(ShedTwillTestCase):
    """Verify that the code correctly handles circular dependencies down to n levels."""

    requires_galaxy = True

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_convert_repository(self):
        """Create and populate convert_chars_0050."""
        category = self.create_category(name=category_name, description=category_description)
        global running_standalone
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
        """Create and populate convert_chars_0050."""
        category = self.create_category(name=category_name, description=category_description)
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

    def test_0015_create_emboss_datatypes_repository(self):
        """noop now..."""
        pass

    def test_0020_create_emboss_repository(self):
        """Create and populate emboss_0050."""
        category = self.create_category(name=category_name, description=category_description)
        repository = self.get_or_create_repository(
            name=emboss_repository_name,
            description=emboss_repository_description,
            long_description=emboss_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(repository):
            self.commit_tar_to_repository(
                repository,
                "emboss/emboss.tar",
                commit_message="Uploaded emboss tarball.",
            )

    def test_0025_create_filtering_repository(self):
        """Create and populate filtering_0050."""
        category = self.create_category(name=category_name, description=category_description)
        repository = self.get_or_create_repository(
            name=filtering_repository_name,
            description=filtering_repository_description,
            long_description=filtering_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(repository):
            self.commit_tar_to_repository(
                repository,
                "filtering/filtering_1.1.0.tar",
                commit_message="Uploaded filtering 1.1.0 tarball.",
            )

    def test_0030_create_freebayes_repository(self):
        """Create and populate freebayes_0050."""
        category = self.create_category(name=category_name, description=category_description)
        repository = self.get_or_create_repository(
            name=freebayes_repository_name,
            description=freebayes_repository_description,
            long_description=freebayes_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(repository):
            self.commit_tar_to_repository(
                repository,
                "freebayes/freebayes.tar",
                commit_message="Uploaded freebayes tarball.",
            )

    def test_0035_create_bismark_repository(self):
        """Create and populate bismark_0050."""
        category = self.create_category(name=category_name, description=category_description)
        repository = self.get_or_create_repository(
            name=bismark_repository_name,
            description=bismark_repository_description,
            long_description=bismark_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(repository):
            self.user_populator().setup_bismark_repo(repository, end=1)

    def test_0040_create_and_upload_dependency_definitions(self):
        """Set up the dependency structure."""
        global running_standalone
        if running_standalone:
            column_repository = self._get_repository_by_name_and_owner(column_repository_name, common.test_user_1_name)
            convert_repository = self._get_repository_by_name_and_owner(
                convert_repository_name, common.test_user_1_name
            )
            emboss_repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
            filtering_repository = self._get_repository_by_name_and_owner(
                filtering_repository_name, common.test_user_1_name
            )
            freebayes_repository = self._get_repository_by_name_and_owner(
                freebayes_repository_name, common.test_user_1_name
            )
            bismark_repository = self._get_repository_by_name_and_owner(
                bismark_repository_name, common.test_user_1_name
            )
            dependency_xml_path = self.generate_temp_path("test_1050", additional_paths=["dependencies"])
            # convert_chars depends on column_maker
            # column_maker depends on convert_chars
            # emboss depends on bismark
            # freebayes depends on freebayes, emboss, bismark, and column_maker
            # filtering depends on emboss
            column_tuple = (
                self.url,
                column_repository.name,
                column_repository.owner,
                self.get_repository_tip(column_repository),
            )
            convert_tuple = (
                self.url,
                convert_repository.name,
                convert_repository.owner,
                self.get_repository_tip(convert_repository),
            )
            freebayes_tuple = (
                self.url,
                freebayes_repository.name,
                freebayes_repository.owner,
                self.get_repository_tip(freebayes_repository),
            )
            emboss_tuple = (
                self.url,
                emboss_repository.name,
                emboss_repository.owner,
                self.get_repository_tip(emboss_repository),
            )
            bismark_tuple = (
                self.url,
                bismark_repository.name,
                bismark_repository.owner,
                self.get_repository_tip(bismark_repository),
            )
            self.create_repository_dependency(
                repository=convert_repository, repository_tuples=[column_tuple], filepath=dependency_xml_path
            )
            self.create_repository_dependency(
                repository=column_repository, repository_tuples=[convert_tuple], filepath=dependency_xml_path
            )
            self.create_repository_dependency(
                repository=emboss_repository, repository_tuples=[bismark_tuple], filepath=dependency_xml_path
            )
            self.create_repository_dependency(
                repository=freebayes_repository,
                repository_tuples=[freebayes_tuple, emboss_tuple, column_tuple],
                filepath=dependency_xml_path,
            )
            self.create_repository_dependency(
                repository=filtering_repository, repository_tuples=[emboss_tuple], filepath=dependency_xml_path
            )

    def test_0045_verify_repository_dependencies(self):
        """Verify that the generated dependency circle does not cause an infinite loop.
        Expected structure:

        id: 2 key: http://toolshed.local:10001__ESEP__filtering__ESEP__test__ESEP__871602b4276b
            ['http://toolshed.local:10001', 'emboss_5', 'test', '8de5fe0d7b04']
             id: 3 key: http://toolshed.local:10001__ESEP__emboss_datatypes__ESEP__test__ESEP__dbd4f68bf507
                 ['http://toolshed.local:10001', 'freebayes', 'test', 'f40028114098']
             id: 4 key: http://toolshed.local:10001__ESEP__freebayes__ESEP__test__ESEP__f40028114098
                 ['http://toolshed.local:10001', 'emboss_datatypes', 'test', 'dbd4f68bf507']
                 ['http://toolshed.local:10001', 'emboss_5', 'test', '8de5fe0d7b04']
                 ['http://toolshed.local:10001', 'column_maker', 'test', '83e956bdbac0']
             id: 5 key: http://toolshed.local:10001__ESEP__column_maker__ESEP__test__ESEP__83e956bdbac0
                 ['http://toolshed.local:10001', 'convert_chars', 'test', 'b28134220c8a']
             id: 6 key: http://toolshed.local:10001__ESEP__convert_chars__ESEP__test__ESEP__b28134220c8a
                 ['http://toolshed.local:10001', 'column_maker', 'test', '83e956bdbac0']
             id: 7 key: http://toolshed.local:10001__ESEP__emboss_5__ESEP__test__ESEP__8de5fe0d7b04
                 ['http://toolshed.local:10001', 'emboss_datatypes', 'test', 'dbd4f68bf507']
        """
        emboss_repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
        filtering_repository = self._get_repository_by_name_and_owner(
            filtering_repository_name, common.test_user_1_name
        )
        freebayes_repository = self._get_repository_by_name_and_owner(
            freebayes_repository_name, common.test_user_1_name
        )
        column_repository = self._get_repository_by_name_and_owner(column_repository_name, common.test_user_1_name)
        convert_repository = self._get_repository_by_name_and_owner(convert_repository_name, common.test_user_1_name)
        bismark_repository = self._get_repository_by_name_and_owner(bismark_repository_name, common.test_user_1_name)
        self.check_repository_dependency(convert_repository, column_repository)
        self.check_repository_dependency(column_repository, convert_repository)
        self.check_repository_dependency(emboss_repository, bismark_repository)
        self.check_repository_dependency(filtering_repository, emboss_repository)
        for repository in [bismark_repository, emboss_repository, column_repository]:
            self.check_repository_dependency(freebayes_repository, repository)
        freebayes_dependencies = [
            freebayes_repository,
            emboss_repository,
            column_repository,
        ]
        strings_displayed = [
            f"{freebayes_repository.name} depends on {', '.join(repo.name for repo in freebayes_dependencies)}."
        ]
        if not self.is_v2:
            self.display_manage_repository_page(freebayes_repository, strings_displayed=strings_displayed)

    def test_0050_verify_tool_dependencies(self):
        """Check that freebayes and emboss display tool dependencies."""
        freebayes_repository = self._get_repository_by_name_and_owner(
            freebayes_repository_name, common.test_user_1_name
        )
        emboss_repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
        if not self.is_v2:
            self.display_manage_repository_page(
                freebayes_repository,
                strings_displayed=["freebayes", "0.9.4_9696d0ce8a9", "samtools", "0.1.18", "Tool dependencies"],
            )
            self.display_manage_repository_page(
                emboss_repository, strings_displayed=["Tool dependencies", "emboss", "5.0.0", "package"]
            )

    def test_0055_install_column_repository(self):
        """Install column_maker with repository dependencies."""
        self._install_repository(
            column_repository_name,
            common.test_user_1_name,
            category_name,
            install_tool_dependencies=False,
            install_repository_dependencies=True,
            new_tool_panel_section_label="column_maker",
        )
        # This should result in column_maker and convert_chars being installed, and the rest never installed.
        installed_repositories = [
            (column_repository_name, common.test_user_1_name),
            (convert_repository_name, common.test_user_1_name),
        ]
        strings_displayed = ["column_maker_0050", "convert_chars_0050"]
        strings_not_displayed = [
            "emboss_0050",
            "filtering_0050",
            "freebayes_0050",
            "bismark_0050",
        ]
        self._assert_has_installed_repos_with_names(*strings_displayed)
        self._assert_has_no_installed_repos_with_names(*strings_not_displayed)
        self.verify_installed_repositories(installed_repositories=installed_repositories)

    def test_0060_install_emboss_repository(self):
        """Install emboss_5 with repository dependencies."""
        global running_standalone
        self._install_repository(
            emboss_repository_name,
            common.test_user_1_name,
            category_name,
            install_tool_dependencies=False,
            install_repository_dependencies=True,
            new_tool_panel_section_label="emboss_5_0050",
        )
        # Now we have emboss, bismark, column_maker, and convert_chars installed, filtering and freebayes never installed.
        installed_repositories = [
            (column_repository_name, common.test_user_1_name),
            (emboss_repository_name, common.test_user_1_name),
            (convert_repository_name, common.test_user_1_name),
            (bismark_repository_name, common.test_user_1_name),
        ]
        strings_displayed = [
            "emboss_0050",
            "column_maker_0050",
            "convert_chars_0050",
            "bismark_0050",
        ]
        strings_not_displayed = ["filtering_0050", "freebayes_0050"]
        self._assert_has_installed_repos_with_names(*strings_displayed)
        self._assert_has_no_installed_repos_with_names(*strings_not_displayed)
        self.verify_installed_repositories(installed_repositories)

    def test_0065_deactivate_bismark_repository(self):
        """Deactivate bismark and verify things are okay."""
        repository = self._get_installed_repository_by_name_owner(bismark_repository_name, common.test_user_1_name)
        self.deactivate_repository(repository)
        # Now we have emboss, bismark, column_maker, and convert_chars installed, filtering and freebayes never installed.
        installed_repositories = [
            (column_repository_name, common.test_user_1_name),
            (emboss_repository_name, common.test_user_1_name),
            (convert_repository_name, common.test_user_1_name),
        ]
        strings_displayed = ["emboss_0050", "column_maker_0050", "convert_chars_0050"]
        strings_not_displayed = ["bismark", "filtering_0050", "freebayes_0050"]
        self._assert_has_installed_repos_with_names(*strings_displayed)
        self._assert_has_no_installed_repos_with_names(*strings_not_displayed)
        self.verify_installed_repositories(installed_repositories)

    def test_0070_uninstall_emboss_repository(self):
        """Uninstall the emboss_5 repository."""
        repository = self._get_installed_repository_by_name_owner(emboss_repository_name, common.test_user_1_name)
        self._uninstall_repository(repository)
        self._assert_has_no_installed_repos_with_names(repository.name)
        self._refresh_tool_shed_repository(repository)
        self.check_galaxy_repository_tool_panel_section(repository, "emboss_5_0050")
        # Now we have bismark, column_maker, and convert_chars installed, filtering and freebayes never installed,
        # and emboss uninstalled.
        installed_repositories = [
            (column_repository_name, common.test_user_1_name),
            (convert_repository_name, common.test_user_1_name),
        ]
        strings_displayed = ["column_maker_0050", "convert_chars_0050"]
        strings_not_displayed = ["emboss_0050", "filtering_0050", "freebayes_0050"]
        self._assert_has_installed_repos_with_names(*strings_displayed)
        self._assert_has_no_installed_repos_with_names(*strings_not_displayed)
        self.verify_installed_repositories(installed_repositories)

    def test_0075_install_freebayes_repository(self):
        """Install freebayes with repository dependencies. This should also automatically reactivate bismark and reinstall emboss_5."""
        strings_displayed = ["Handle", "tool dependencies", "freebayes", "0.9.4_9696d0ce8a9", "samtools", "0.1.18"]
        self._install_repository(
            freebayes_repository_name,
            common.test_user_1_name,
            category_name,
            install_tool_dependencies=False,
            install_repository_dependencies=True,
            new_tool_panel_section_label="freebayes",
        )
        self._assert_has_installed_repos_with_names("emboss_0050")
        # Installing freebayes should automatically reinstall emboss and reactivate bismark.
        # Now column_maker, convert_chars, emboss, freebayes, and bismark should be installed.
        installed_repositories = [
            (column_repository_name, common.test_user_1_name),
            (emboss_repository_name, common.test_user_1_name),
            (freebayes_repository_name, common.test_user_1_name),
            (convert_repository_name, common.test_user_1_name),
            (bismark_repository_name, common.test_user_1_name),
        ]
        strings_displayed = [
            "emboss_0050",
            "column_maker_0050",
            "convert_chars_0050",
            "bismark_0050",
            "freebayes_0050",
        ]
        strings_not_displayed = ["filtering_0050"]
        self._assert_has_installed_repos_with_names(*strings_displayed)
        self._assert_has_no_installed_repos_with_names(*strings_not_displayed)
        self.verify_installed_repositories(installed_repositories)
