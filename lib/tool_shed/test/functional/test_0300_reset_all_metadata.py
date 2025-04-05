from typing import Dict

import pytest

from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

column_maker_repository_name = "column_maker_0020"
column_maker_repository_description = "A flexible aligner."
column_maker_repository_long_description = "A flexible aligner and methylation caller for Bisulfite-Seq applications."

emboss_repository_description = "Galaxy wrappers for Emboss version 5.0.0 tools"
emboss_repository_long_description = "Galaxy wrappers for Emboss version 5.0.0 tools"

emboss_repository_name = "emboss_0050"
emboss_5_repository_name = "emboss_5_0050"
emboss_6_repository_name = "emboss_6_0050"

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

category_0050_name = "Test 0050 Circular Dependencies 5 Levels"
category_0050_description = "Test circular dependency features"

running_standalone = False


class TestResetAllRepositoryMetadata(ShedTwillTestCase):
    """Verify that the "Reset selected metadata" feature works."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_filtering_repository(self):
        """Create and populate the filtering_0000 repository."""
        global running_standalone
        self.login(email=common.admin_email, username=common.admin_username)
        category_0000 = self.create_category(
            name="Test 0000 Basic Repository Features 1", description="Test 0000 Basic Repository Features 1"
        )
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name="filtering_0000",
            description="Galaxy's filtering tool",
            long_description="Long description of Galaxy's filtering tool",
            owner=common.test_user_1_name,
            category=category_0000,
        )
        if self.repository_is_new(repository):
            running_standalone = True
            self.commit_tar_to_repository(
                repository,
                "filtering/filtering_1.1.0.tar",
                commit_message="Uploaded filtering 1.1.0 tarball.",
            )
            self.add_tar_to_repository(repository, "filtering/filtering_2.2.0.tar")

    def test_0010_create_freebayes_repository(self):
        """Create and populate the freebayes_0010 repository."""
        self.login(email=common.admin_email, username=common.admin_username)
        category_0010 = self.create_category(
            name="Test 0010 Repository With Tool Dependencies",
            description="Tests for a repository with tool dependencies.",
        )
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name="freebayes_0010",
            description="Galaxy's freebayes tool",
            long_description="Long description of Galaxy's freebayes tool",
            owner=common.test_user_1_name,
            category=category_0010,
            strings_displayed=[],
        )
        if running_standalone:
            self.setup_freebayes_0010_repo(repository)

    def test_0015_create_datatypes_0020_repository(self):
        """Create and populate the column_maker_0020 repository."""
        if running_standalone:
            self.login(email=common.admin_email, username=common.admin_username)
            category_0020 = self.create_category(
                name="Test 0020 Basic Repository Dependencies",
                description="Testing basic repository dependency features.",
            )
            self.login(email=common.test_user_1_email, username=common.test_user_1_name)
            repository = self.get_or_create_repository(
                name="column_maker_0020",
                description=column_maker_repository_description,
                long_description=column_maker_repository_long_description,
                owner=common.test_user_1_name,
                category=category_0020,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                repository,
                "column_maker/column_maker.tar",
                commit_message="Uploaded column_maker tarball.",
            )

    def test_0020_create_emboss_0020_repository(self):
        """Create and populate the emboss_0020 repository."""
        if running_standalone:
            self.login(email=common.admin_email, username=common.admin_username)
            category_0020 = self.create_category(
                name="Test 0020 Basic Repository Dependencies",
                description="Testing basic repository dependency features.",
            )
            self.login(email=common.test_user_1_email, username=common.test_user_1_name)
            repository = self.get_or_create_repository(
                name="emboss_0020",
                description=emboss_repository_long_description,
                long_description=emboss_repository_long_description,
                owner=common.test_user_1_name,
                category=category_0020,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                repository,
                "emboss/emboss.tar",
                commit_message="Uploaded emboss.tar",
            )

    def test_0025_create_emboss_datatypes_0030_repository(self):
        """Create and populate the emboss_0030 repository."""
        if running_standalone:
            self.login(email=common.admin_email, username=common.admin_username)
            category_0030 = self.create_category(
                name="Test 0030 Repository Dependency Revisions",
                description="Testing repository dependencies by revision.",
            )
            self.login(email=common.test_user_1_email, username=common.test_user_1_name)
            column_maker_repository = self.get_or_create_repository(
                name="column_maker_0030",
                description=column_maker_repository_description,
                long_description=column_maker_repository_long_description,
                owner=common.test_user_1_name,
                category=category_0030,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                column_maker_repository,
                "column_maker/column_maker.tar",
                commit_message="Uploaded column_maker tarball.",
            )

    def test_0030_create_emboss_5_repository(self):
        """Create and populate the emboss_5_0030 repository."""
        if running_standalone:
            self.login(email=common.admin_email, username=common.admin_username)
            category_0030 = self.create_category(
                name="Test 0030 Repository Dependency Revisions",
                description="Testing repository dependencies by revision.",
            )
            self.login(email=common.test_user_1_email, username=common.test_user_1_name)
            emboss_5_repository = self.get_or_create_repository(
                name="emboss_5_0030",
                description=emboss_repository_description,
                long_description=emboss_repository_long_description,
                owner=common.test_user_1_name,
                category=category_0030,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                emboss_5_repository,
                "emboss/emboss.tar",
                commit_message="Uploaded emboss.tar",
            )

    def test_0035_create_emboss_6_repository(self):
        """Create and populate the emboss_6_0030 repository."""
        if running_standalone:
            self.login(email=common.admin_email, username=common.admin_username)
            category_0030 = self.create_category(
                name="Test 0030 Repository Dependency Revisions",
                description="Testing repository dependencies by revision.",
            )
            self.login(email=common.test_user_1_email, username=common.test_user_1_name)
            emboss_6_repository = self.get_or_create_repository(
                name="emboss_6_0030",
                description=emboss_repository_description,
                long_description=emboss_repository_long_description,
                owner=common.test_user_1_name,
                category=category_0030,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                emboss_6_repository,
                "emboss/emboss.tar",
                commit_message="Uploaded emboss.tar",
            )

    def test_0040_create_emboss_0030_repository(self):
        """Create and populate the emboss_0030 repository."""
        if running_standalone:
            self.login(email=common.admin_email, username=common.admin_username)
            category_0030 = self.create_category(
                name="Test 0030 Repository Dependency Revisions",
                description="Testing repository dependencies by revision.",
            )
            self.login(email=common.test_user_1_email, username=common.test_user_1_name)
            emboss_repository = self.get_or_create_repository(
                name="emboss_0030",
                description=emboss_repository_description,
                long_description=emboss_repository_long_description,
                owner=common.test_user_1_name,
                category=category_0030,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                emboss_repository,
                "emboss/emboss.tar",
                commit_message="Uploaded emboss.tar",
            )

    def test_0045_create_repository_dependencies_for_0030(self):
        """Create the dependency structure for test 0030."""
        if running_standalone:
            column_maker_repository = self._get_repository_by_name_and_owner(
                "column_maker_0030", common.test_user_1_name
            )
            emboss_repository = self._get_repository_by_name_and_owner("emboss_0030", common.test_user_1_name)
            emboss_5_repository = self._get_repository_by_name_and_owner("emboss_5_0030", common.test_user_1_name)
            emboss_6_repository = self._get_repository_by_name_and_owner("emboss_6_0030", common.test_user_1_name)
            repository_dependencies_path = self.generate_temp_path("test_0330", additional_paths=["emboss"])
            column_maker_tuple = (
                self.url,
                column_maker_repository.name,
                column_maker_repository.owner,
                self.get_repository_tip(column_maker_repository),
            )
            emboss_5_tuple = (
                self.url,
                emboss_5_repository.name,
                emboss_5_repository.owner,
                self.get_repository_tip(emboss_5_repository),
            )
            emboss_6_tuple = (
                self.url,
                emboss_6_repository.name,
                emboss_6_repository.owner,
                self.get_repository_tip(emboss_6_repository),
            )
            self.create_repository_dependency(
                repository=emboss_5_repository,
                repository_tuples=[column_maker_tuple],
                filepath=repository_dependencies_path,
            )
            self.create_repository_dependency(
                repository=emboss_6_repository,
                repository_tuples=[column_maker_tuple],
                filepath=repository_dependencies_path,
            )
            self.create_repository_dependency(
                repository=emboss_repository, repository_tuples=[emboss_5_tuple], filepath=repository_dependencies_path
            )
            self.create_repository_dependency(
                repository=emboss_repository, repository_tuples=[emboss_6_tuple], filepath=repository_dependencies_path
            )

    def test_0050_create_freebayes_repository(self):
        """Create and populate the freebayes_0040 repository."""
        self.login(email=common.admin_email, username=common.admin_username)
        category_0040 = self.create_category(
            name="test_0040_repository_circular_dependencies",
            description="Testing handling of circular repository dependencies.",
        )
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name="freebayes_0040",
            description="Galaxy's freebayes tool",
            long_description="Long description of Galaxy's freebayes tool",
            owner=common.test_user_1_name,
            category=category_0040,
            strings_displayed=[],
        )
        if running_standalone:
            self.commit_tar_to_repository(
                repository,
                "freebayes/freebayes.tar",
                commit_message="Uploaded freebayes tarball.",
            )

    def test_0055_create_filtering_repository(self):
        """Create and populate the filtering_0040 repository."""
        if running_standalone:
            self.login(email=common.admin_email, username=common.admin_username)
            category_0040 = self.create_category(
                name="test_0040_repository_circular_dependencies",
                description="Testing handling of circular repository dependencies.",
            )
            self.login(email=common.test_user_1_email, username=common.test_user_1_name)
            repository = self.get_or_create_repository(
                name="filtering_0040",
                description="Galaxy's filtering tool",
                long_description="Long description of Galaxy's filtering tool",
                owner=common.test_user_1_name,
                category=category_0040,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                repository,
                "filtering/filtering_1.1.0.tar",
                commit_message="Uploaded filtering 1.1.0 tarball.",
            )

    def test_0060_create_dependency_structure(self):
        """Create the dependency structure for test 0040."""
        if running_standalone:
            freebayes_repository = self._get_repository_by_name_and_owner("freebayes_0040", common.test_user_1_name)
            filtering_repository = self._get_repository_by_name_and_owner("filtering_0040", common.test_user_1_name)
            repository_dependencies_path = self.generate_temp_path("test_0340", additional_paths=["dependencies"])
            freebayes_tuple = (
                self.url,
                freebayes_repository.name,
                freebayes_repository.owner,
                self.get_repository_tip(freebayes_repository),
            )
            filtering_tuple = (
                self.url,
                filtering_repository.name,
                filtering_repository.owner,
                self.get_repository_tip(filtering_repository),
            )
            self.create_repository_dependency(
                repository=filtering_repository,
                repository_tuples=[freebayes_tuple],
                filepath=repository_dependencies_path,
            )
            self.create_repository_dependency(
                repository=freebayes_repository,
                repository_tuples=[filtering_tuple],
                filepath=repository_dependencies_path,
            )

    def test_0065_create_convert_repository(self):
        """Create and populate convert_chars_0050."""
        if running_standalone:
            self.login(email=common.admin_email, username=common.admin_username)
            category = self.create_category(name=category_0050_name, description=category_0050_description)
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

    def test_0070_create_column_repository(self):
        """Create and populate convert_chars_0050."""
        if running_standalone:
            self.login(email=common.admin_email, username=common.admin_username)
            category = self.create_category(name=category_0050_name, description=category_0050_description)
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

    def test_0075_create_emboss_datatypes_repository(self):
        """noop now..."""

    def test_0080_create_emboss_repository(self):
        """Create and populate emboss_0050."""
        if running_standalone:
            self.login(email=common.admin_email, username=common.admin_username)
            category = self.create_category(name=category_0050_name, description=category_0050_description)
            self.login(email=common.test_user_1_email, username=common.test_user_1_name)
            repository = self.get_or_create_repository(
                name=emboss_repository_name,
                description=emboss_repository_description,
                long_description=emboss_repository_long_description,
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                repository,
                "emboss/emboss.tar",
                commit_message="Uploaded emboss tarball.",
            )

    def test_0085_create_filtering_repository(self):
        """Create and populate filtering_0050."""
        if running_standalone:
            self.login(email=common.admin_email, username=common.admin_username)
            category = self.create_category(name=category_0050_name, description=category_0050_description)
            self.login(email=common.test_user_1_email, username=common.test_user_1_name)
            filtering_repository = self.get_or_create_repository(
                name=filtering_repository_name,
                description=filtering_repository_description,
                long_description=filtering_repository_long_description,
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                filtering_repository,
                "filtering/filtering_1.1.0.tar",
                commit_message="Uploaded filtering 1.1.0 tarball.",
            )

    def test_0090_create_freebayes_repository(self):
        """Create and populate freebayes_0050."""
        if running_standalone:
            self.login(email=common.admin_email, username=common.admin_username)
            category = self.create_category(name=category_0050_name, description=category_0050_description)
            self.login(email=common.test_user_1_email, username=common.test_user_1_name)
            repository = self.get_or_create_repository(
                name=freebayes_repository_name,
                description=freebayes_repository_description,
                long_description=freebayes_repository_long_description,
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                repository,
                "freebayes/freebayes.tar",
                commit_message="Uploaded freebayes tarball.",
            )

    def test_0095_create_bismark_repository(self):
        """Create and populate bismark_0050."""
        if running_standalone:
            self.login(email=common.admin_email, username=common.admin_username)
            category = self.create_category(name=category_0050_name, description=category_0050_description)
            self.login(email=common.test_user_1_email, username=common.test_user_1_name)
            repository = self.get_or_create_repository(
                name=bismark_repository_name,
                description=bismark_repository_description,
                long_description=bismark_repository_long_description,
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.user_populator().setup_bismark_repo(repository, end=1)

    def test_0100_create_and_upload_dependency_definitions(self):
        """Create the dependency structure for test 0050."""
        if running_standalone:
            self.login(email=common.test_user_1_email, username=common.test_user_1_name)
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
            dependency_xml_path = self.generate_temp_path("test_0050", additional_paths=["freebayes"])
            # convert_chars depends on column_maker
            # column_maker depends on convert_chars
            # emboss depends on emboss_datatypes
            # emboss_datatypes depends on bismark
            # freebayes depends on freebayes, emboss, emboss_datatypes, and column_maker
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
                repository_tuples=[freebayes_tuple, bismark_tuple, emboss_tuple, column_tuple],
                filepath=dependency_xml_path,
            )
            self.create_repository_dependency(
                repository=filtering_repository, repository_tuples=[emboss_tuple], filepath=dependency_xml_path
            )

    @pytest.mark.xfail
    def test_0110_reset_metadata_on_all_repositories(self):
        """Reset metadata on all repositories, then verify that it has not changed."""
        self.login(email=common.admin_email, username=common.admin_username)
        old_metadata: Dict[str, Dict] = {}
        new_metadata: Dict[str, Dict] = {}
        repositories = self.test_db_util.get_all_repositories()
        for repository in repositories:
            old_metadata[self.security.encode_id(repository.id)] = {}
            for metadata in self.get_repository_metadata_for_db_object(repository):
                old_metadata[self.security.encode_id(repository.id)][metadata.changeset_revision] = metadata.metadata
        self.reset_metadata_on_selected_repositories(list(old_metadata.keys()))
        for repository in repositories:
            new_metadata[self.security.encode_id(repository.id)] = {}
            for metadata in self.get_repository_metadata_for_db_object(repository):
                new_metadata[self.security.encode_id(repository.id)][metadata.changeset_revision] = metadata.metadata
            if (
                old_metadata[self.security.encode_id(repository.id)]
                != new_metadata[self.security.encode_id(repository.id)]
            ):
                raise AssertionError(f"Metadata changed after reset for repository {repository.name}.")
