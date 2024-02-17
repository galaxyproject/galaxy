from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

column_maker_repository_name = "column_maker_0020"
column_maker_repository_description = "A flexible aligner."
column_maker_repository_long_description = "A flexible aligner and methylation caller for Bisulfite-Seq applications."

column_repository_name = "column_maker_0030"
column_repository_description = "Add column"
column_repository_long_description = "Compute an expression on every row"

emboss_repository_description = "Galaxy wrappers for Emboss version 5.0.0 tools"
emboss_repository_long_description = "Galaxy wrappers for Emboss version 5.0.0 tools"
filtering_repository_description = "Galaxy's filtering tool for test 0040"
filtering_repository_long_description = "Long description of Galaxy's filtering tool for test 0040"

category_0000_name = "Test 0000 Basic Repository Features 1"
category_0001_name = "Test 0000 Basic Repository Features 2"
category_0010_name = "Test 0010 Repository With Tool Dependencies"
category_0020_name = "Test 0020 Basic Repository Dependencies"
category_0030_name = "Test 0030 Repository Dependency Revisions"
category_0040_name = "test_0040_repository_circular_dependencies"
category_0050_name = "test_0050_repository_n_level_circular_dependencies"
category_0060_name = "Test 0060 Workflow Features"

"""
This script will run in one of two possible ways:

1. Directly, by calling sh run_functional_tests.sh -toolshed test/tool_shed/functional/test_1300_reset_all_metadata.py. -or-
2. After the previous test scripts have completed.

In the first case, it is desirable to have the Galaxy database in a state that is as close as possible to the state it would
be in following the second case. This means explicitly installing whatever repositories would be in an installed state following
the previous test scripts.
"""

base_datatypes_count = 0
repository_datatypes_count = 0
running_standalone = False


class TestResetInstalledRepositoryMetadata(ShedTwillTestCase):
    """Verify that the "Reset selected metadata" feature works."""

    requires_galaxy = True

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_categories(self):
        """Create the categories for the repositories in this test script."""
        self.login(email=common.admin_email, username=common.admin_username)
        self.create_category(name=category_0000_name, description="Test 0000 Basic Repository Features 1")
        self.create_category(name=category_0001_name, description="Test 0000 Basic Repository Features 2")
        self.create_category(name=category_0010_name, description="Tests for a repository with tool dependencies.")
        self.create_category(name=category_0020_name, description="Testing basic repository dependency features.")
        self.create_category(name=category_0030_name, description="Testing repository dependencies by revision.")
        self.create_category(
            name=category_0040_name, description="Testing handling of circular repository dependencies."
        )
        self.create_category(
            name=category_0050_name, description="Testing handling of circular repository dependencies to n levels."
        )
        self.create_category(name=category_0060_name, description="Test 0060 - Workflow Features")

    def test_0010_create_repositories_from_0000_series(self):
        """Create repository filtering_0000 if necessary."""
        global running_standalone
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        category = self.create_category(name=category_0000_name, description="")
        repository = self.get_or_create_repository(
            name="filtering_0000",
            description="Galaxy's filtering tool",
            long_description="Long description of Galaxy's filtering tool",
            owner=common.test_user_1_name,
            category=category,
        )
        if self.repository_is_new(repository):
            running_standalone = True
            self.commit_tar_to_repository(
                repository,
                "filtering/filtering_1.1.0.tar",
                commit_message="Uploaded filtering 1.1.0 tarball.",
            )
            self.add_tar_to_repository(repository, "filtering/filtering_2.2.0.tar")

    def test_0015_create_repositories_from_0010_series(self):
        """Create repository freebayes_0010."""
        category = self.create_category(name=category_0010_name, description="")
        repository = self.get_or_create_repository(
            name="freebayes_0010",
            description="Galaxy's freebayes tool",
            long_description="Long description of Galaxy's freebayes tool",
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(repository):
            self.setup_freebayes_0010_repo(repository)

    def test_0020_create_repositories_from_0020_series(self):
        """Create repositories emboss_0020 and column_maker_0020 if necessary."""
        category = self.create_category(name=category_0020_name, description="")
        column_maker_repository = self.get_or_create_repository(
            name=column_maker_repository_name,
            description=column_maker_repository_description,
            long_description=column_maker_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(column_maker_repository):
            self.commit_tar_to_repository(
                column_maker_repository,
                "column_maker/column_maker.tar",
                commit_message="Uploaded column_maker tarball.",
            )
            repository = self.get_or_create_repository(
                name="emboss_0020",
                description="Galaxy wrappers for Emboss version 5.0.0 tools",
                long_description="Galaxy wrappers for Emboss version 5.0.0 tools",
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                repository,
                "emboss/emboss.tar",
                commit_message="Uploaded emboss.tar",
            )

    def test_0025_create_repositories_from_0030_series(self):
        """Create repositories emboss_0030, emboss_5_0030, emboss_6_0030, and emboss_datatypes_0030."""
        global repository_datatypes_count
        category = self.create_category(name=category_0030_name, description="")
        column_maker_repository = self.get_or_create_repository(
            name="column_maker_0030",
            description=column_repository_description,
            long_description=column_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(column_maker_repository):
            self.commit_tar_to_repository(
                column_maker_repository,
                "column_maker/column_maker.tar",
                commit_message="Uploaded bismark tarball.",
            )
            emboss_5_repository = self.get_or_create_repository(
                name="emboss_5_0030",
                description=emboss_repository_description,
                long_description=emboss_repository_long_description,
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                emboss_5_repository,
                "emboss/emboss.tar",
                commit_message="Uploaded emboss.tar",
            )
            repository_dependencies_path = self.generate_temp_path("test_0330", additional_paths=["emboss", "5"])
            dependency_tuple = (
                self.url,
                column_maker_repository.name,
                column_maker_repository.owner,
                self.get_repository_tip(column_maker_repository),
            )
            self.create_repository_dependency(
                repository=emboss_5_repository,
                repository_tuples=[dependency_tuple],
                filepath=repository_dependencies_path,
            )
            emboss_6_repository = self.get_or_create_repository(
                name="emboss_6_0030",
                description=emboss_repository_description,
                long_description=emboss_repository_long_description,
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                emboss_6_repository,
                "emboss/emboss.tar",
                commit_message="Uploaded emboss.tar",
            )
            repository_dependencies_path = self.generate_temp_path("test_0330", additional_paths=["emboss", "6"])
            dependency_tuple = (
                self.url,
                column_maker_repository.name,
                column_maker_repository.owner,
                self.get_repository_tip(column_maker_repository),
            )
            self.create_repository_dependency(
                repository=emboss_6_repository,
                repository_tuples=[dependency_tuple],
                filepath=repository_dependencies_path,
            )
            emboss_repository = self.get_or_create_repository(
                name="emboss_0030",
                description=emboss_repository_description,
                long_description=emboss_repository_long_description,
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                emboss_repository,
                "emboss/emboss.tar",
                commit_message="Uploaded emboss.tar",
            )
            repository_dependencies_path = self.generate_temp_path("test_0330", additional_paths=["emboss", "5"])
            dependency_tuple = (
                self.url,
                emboss_5_repository.name,
                emboss_5_repository.owner,
                self.get_repository_tip(emboss_5_repository),
            )
            self.create_repository_dependency(
                repository=emboss_repository,
                repository_tuples=[dependency_tuple],
                filepath=repository_dependencies_path,
            )
            dependency_tuple = (
                self.url,
                emboss_6_repository.name,
                emboss_6_repository.owner,
                self.get_repository_tip(emboss_6_repository),
            )
            self.create_repository_dependency(
                repository=emboss_repository,
                repository_tuples=[dependency_tuple],
                filepath=repository_dependencies_path,
            )

    def test_0030_create_repositories_from_0040_series(self):
        """Create repositories freebayes_0040 and filtering_0040."""
        category = self.create_category(name=category_0040_name, description="")
        repository = self.get_or_create_repository(
            name="freebayes_0040",
            description="Galaxy's freebayes tool",
            long_description="Long description of Galaxy's freebayes tool",
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(repository):
            self.commit_tar_to_repository(
                repository,
                "freebayes/freebayes.tar",
                commit_message="Uploaded the tool tarball.",
            )
            repository = self.get_or_create_repository(
                name="filtering_0040",
                description=filtering_repository_description,
                long_description=filtering_repository_long_description,
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                repository,
                "filtering/filtering_1.1.0.tar",
                commit_message="Uploaded the tool tarball for filtering 1.1.0.",
            )
            repository = self._get_repository_by_name_and_owner("freebayes_0040", common.test_user_1_name)
            filtering_repository = self._get_repository_by_name_and_owner("filtering_0040", common.test_user_1_name)
            repository_dependencies_path = self.generate_temp_path("test_1340", additional_paths=["filtering"])
            repository_tuple = (
                self.url,
                repository.name,
                repository.owner,
                self.get_repository_tip(repository),
            )
            self.create_repository_dependency(
                repository=filtering_repository,
                repository_tuples=[repository_tuple],
                filepath=repository_dependencies_path,
            )
            repository = self._get_repository_by_name_and_owner("filtering_0040", common.test_user_1_name)
            freebayes_repository = self._get_repository_by_name_and_owner("freebayes_0040", common.test_user_1_name)
            repository_dependencies_path = self.generate_temp_path("test_1340", additional_paths=["freebayes"])
            repository_tuple = (
                self.url,
                repository.name,
                repository.owner,
                self.get_repository_tip(repository),
            )
            self.create_repository_dependency(
                repository=freebayes_repository,
                repository_tuples=[repository_tuple],
                filepath=repository_dependencies_path,
            )

    def test_0035_create_repositories_from_0050_series(self):
        """Create repositories emboss_0050, emboss_datatypes_0050, filtering_0050, freebayes_0050."""
        category = self.create_category(name=category_0050_name, description="")
        emboss_repository = self.get_or_create_repository(
            name="emboss_0050",
            description="Galaxy's emboss tool",
            long_description="Long description of Galaxy's emboss tool",
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(emboss_repository):
            filtering_repository = self.get_or_create_repository(
                name="filtering_0050",
                description="Galaxy's filtering tool",
                long_description="Long description of Galaxy's filtering tool",
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            freebayes_repository = self.get_or_create_repository(
                name="freebayes_0050",
                description="Galaxy's freebayes tool",
                long_description="Long description of Galaxy's freebayes tool",
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                emboss_repository,
                "emboss/emboss.tar",
                commit_message="Uploaded emboss.tar",
            )
            self.commit_tar_to_repository(
                freebayes_repository,
                "freebayes/freebayes.tar",
                commit_message="Uploaded freebayes tarball.",
            )
            self.commit_tar_to_repository(
                filtering_repository,
                "filtering/filtering_1.1.0.tar",
                commit_message="Uploaded filtering 1.1.0 tarball.",
            )
            repository_dependencies_path = self.generate_temp_path("test_0350", additional_paths=["emboss"])
            repository_dependencies_path = self.generate_temp_path("test_0350", additional_paths=["filtering"])
            dependency_tuple = (
                self.url,
                emboss_repository.name,
                emboss_repository.owner,
                self.get_repository_tip(emboss_repository),
            )
            self.create_repository_dependency(
                repository=filtering_repository,
                repository_tuples=[dependency_tuple],
                filepath=repository_dependencies_path,
            )
            repository_dependencies_path = self.generate_temp_path("test_0350", additional_paths=["freebayes"])
            dependency_tuple = (
                self.url,
                filtering_repository.name,
                filtering_repository.owner,
                self.get_repository_tip(filtering_repository),
            )
            self.create_repository_dependency(
                repository=emboss_repository,
                repository_tuples=[dependency_tuple],
                filepath=repository_dependencies_path,
            )
            dependency_tuples = [
                (
                    self.url,
                    emboss_repository.name,
                    emboss_repository.owner,
                    self.get_repository_tip(emboss_repository),
                ),
                (
                    self.url,
                    filtering_repository.name,
                    filtering_repository.owner,
                    self.get_repository_tip(filtering_repository),
                ),
                (
                    self.url,
                    freebayes_repository.name,
                    freebayes_repository.owner,
                    self.get_repository_tip(freebayes_repository),
                ),
            ]
            self.create_repository_dependency(
                repository=freebayes_repository,
                repository_tuples=dependency_tuples,
                filepath=repository_dependencies_path,
            )

    def test_9900_install_all_missing_repositories(self):
        """Call the install_repository method to ensure that all required repositories are installed."""
        self._install_repository("filtering_0000", common.test_user_1_name, category_0000_name)
        self._install_repository("freebayes_0010", common.test_user_1_name, category_0010_name)
        self._install_repository("emboss_0020", common.test_user_1_name, category_0020_name)
        self._install_repository("emboss_5_0030", common.test_user_1_name, category_0030_name)
        self._install_repository("freebayes_0050", common.test_user_1_name, category_0050_name)

    def test_9905_reset_metadata_on_all_repositories(self):
        """Reset metadata on all repositories, then verify that it has not changed."""
        repositories = self.get_all_installed_repositories()
        repository_metadata = {}
        for repository in repositories:
            repository_metadata[repository.id] = repository.metadata_
        self.reset_metadata_on_installed_repositories(repositories)
        for repository in self.get_all_installed_repositories():
            old_metadata = repository_metadata[repository.id]
            # When a repository with tools to be displayed in a tool panel section is deactivated and reinstalled,
            # the tool panel section remains in the repository metadata. However, when the repository's metadata
            # is subsequently reset, the tool panel section is removed from the repository metadata. While this
            # is normal and expected behavior, the functional tests assume that repository metadata will not change
            # in any way after a reset. A workaround is to remove the tool panel section from the stored repository
            # metadata dict, in order to eliminate the misleading detection of changed metadata.
            if "tool_panel_section" in old_metadata and "tool_panel_section" not in repository.metadata_:
                del old_metadata["tool_panel_section"]
            assert (
                repository.metadata_ == old_metadata
            ), f"Metadata for {repository.status} repository {repository.name} changed after reset. \nOld: {old_metadata}\nNew: {repository.metadata_}"
