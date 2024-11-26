from tool_shed_client.schema import Repository
from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

column_repository_name = "column_maker_0440"
column_repository_description = "Add column"
column_repository_long_description = "Compute an expression on every row"

convert_repository_name = "convert_chars_0440"
convert_repository_description = "Convert delimiters"
convert_repository_long_description = "Convert delimiters to tab"

bwa_package_repository_name = "bwa_package_0440"
bwa_package_repository_description = "BWA Package Repository"
bwa_package_repository_long_description = "BWA repository with a package tool dependency defined for BWA 0.5.9."

bwa_base_repository_name = "bwa_base_0440"
bwa_base_repository_description = "BWA Base"
bwa_base_repository_long_description = "NT space mapping with BWA"

bwa_tool_dependency_repository_name = "bwa_tool_dependency_0440"
bwa_tool_dependency_repository_description = "BWA Base"
bwa_tool_dependency_repository_long_description = "NT space mapping with BWA"

"""
Simple repository dependencies:

1. Create and populate column_maker_0440 so that it has an installable revision 0.
2. Create and populate convert_chars_0440 so that it has an installable revision 0.
3. Add a valid simple repository_dependencies.xml to convert_chars_0440 that points to the installable revision of column_maker_0440.
4. Make sure the installable revision of convert_chars_0440 is now revision 1 instead of revision 0.
5. Delete repository_dependencies.xml from convert_chars_0440, and make sure convert_chars_0440 now has two installable revisions: 1 and 2

Complex repository dependencies:

1. Create and populate bwa_package_0440 so that it has a valid tool dependency definition and an installable revision 0.
2. Create and populate bwa_base_0440 so that it has an installable revision 0.
3. Add a valid complex repository dependency tool_dependencies.xml to bwa_base_0440 that points to the installable revision 0 of bwa_package_0440.
4. Make sure that bwa_base_0440 installable revision is now revision 1 instead of revision 0.
5. Delete tool_dependencies.xml from bwa_base_0440, and make sure bwa_base_0440 now has two installable revisions: 1 and 2

Tool dependencies:

1. Create and populate bwa_tool_dependency_0440 so that it has a valid tool dependency definition and an installable revision 0.
2. Delete tool_dependencies.xml from bwa_tool_dependency_0440, and make sure that bwa_tool_dependency_0440 still has
   a single installable revision 0.
3. Add the same tool_dependencies.xml file to bwa_tool_dependency_0440, and make sure that bwa_tool_dependency_0440
   still has a single installable revision 0.

"""


class TestDeletedDependencies(ShedTwillTestCase):
    """Test metadata setting when dependency definitions are deleted."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts and login as an admin user.

        Create all the user accounts that are needed for this test script to run independently of other tests.
        Previously created accounts will not be re-created.
        """
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_column_maker_repository(self):
        """Create and populate a repository named column_maker_0440.

        We are at simple repository dependencies, step 1 - Create and populate column_maker_0440 so that it has an installable revision 0.
        """
        category = self.create_category(
            name="Test 0440 Deleted Dependency Definitions",
            description="Description of Deleted Dependency Definitions category for test 0440",
        )
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        strings_displayed = ["Repository <b>column_maker_0440</b> has been created"]
        repository = self.get_or_create_repository(
            name=column_repository_name,
            description=column_repository_description,
            long_description=column_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=strings_displayed,
        )
        self.commit_tar_to_repository(
            repository,
            "column_maker/column_maker.tar",
            commit_message="Uploaded column maker tool tarball.",
        )

    def test_0010_create_convert_chars_repository(self):
        """Create and populate a repository named convert_chars_0440.

        We are at simple repository dependencies, step 2 - Create and populate convert_chars_0440 so that it has an installable revision 0.
        """
        category = self.populator.get_category_with_name("Test 0440 Deleted Dependency Definitions")
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        strings_displayed = ["Repository <b>convert_chars_0440</b> has been created"]
        repository = self.get_or_create_repository(
            name=convert_repository_name,
            description=convert_repository_description,
            long_description=convert_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=strings_displayed,
        )
        self.commit_tar_to_repository(
            repository,
            "convert_chars/convert_chars.tar",
            commit_message="Uploaded convert chars tool tarball.",
        )

    def test_0015_create_dependency_on_convert_chars(self):
        """Create a dependency definition file that specifies column_maker_0440 and upload it to convert_chars_0440.

        We are at simple repository dependencies, step 3 - Add a valid simple repository_dependencies.xml to
        convert_chars_0440 that points to the installable revision of column_maker_0440.
        """
        convert_repository = self._get_repository_by_name_and_owner(convert_repository_name, common.test_user_1_name)
        column_repository = self._get_repository_by_name_and_owner(column_repository_name, common.test_user_1_name)
        dependency_xml_path = self.generate_temp_path("test_0440", additional_paths=["dependencies"])
        column_tuple = (
            self.url,
            column_repository.name,
            column_repository.owner,
            self.get_repository_tip(column_repository),
        )
        # After this, convert_chars_0440 should depend on column_maker_0440.
        self.create_repository_dependency(
            repository=convert_repository,
            repository_tuples=[column_tuple],
            filepath=dependency_xml_path,
            prior_installation_required=True,
        )
        self.check_repository_dependency(convert_repository, column_repository)

    def test_0020_verify_dependency_metadata(self):
        """Verify that uploading the dependency moved metadata to the tip.

        We are at simple repository dependencies, step 4 - Make sure the installable revision of convert_chars_0440 is now
        revision 1 (the tip) instead of revision 0.
        """
        repository = self._get_repository_by_name_and_owner(convert_repository_name, common.test_user_1_name)
        tip = self.get_repository_tip(repository)
        metadata_record = self._get_repository_metadata_by_changeset_revision(repository, tip)
        # Make sure that the new tip is now downloadable, and that there are no other downloadable revisions.
        assert metadata_record.downloadable, "Tip is not downloadable."
        n_downloadable_revisions = len(self._db_repository(repository).downloadable_revisions)
        assert (
            n_downloadable_revisions == 1
        ), f"Repository {repository.name} has {n_downloadable_revisions} downloadable revisions, expected 1."

    def test_0025_delete_repository_dependency(self):
        """Delete the repository_dependencies.xml from convert_chars_0440.

        We are at simple repository dependencies, steps 5 and 6 - Delete repository_dependencies.xml from convert_chars_0440.
        Make sure convert_chars_0440 now has two installable revisions: 1 and 2
        """
        repository = self._get_repository_by_name_and_owner(convert_repository_name, common.test_user_1_name)
        # Record the current tip, so we can verify that it's still a downloadable revision after repository_dependencies.xml
        # is deleted and a new downloadable revision is created.
        old_changeset_revision = self.get_repository_tip(repository)
        self.delete_files_from_repository(repository, filenames=["repository_dependencies.xml"])
        new_changeset_revision = self.get_repository_tip(repository)
        # Check that the old changeset revision is still downloadable.
        metadata_record = self._get_repository_metadata_by_changeset_revision(repository, old_changeset_revision)
        assert (
            metadata_record.downloadable
        ), f"The revision of {repository.name} that contains repository_dependencies.xml is no longer downloadable."
        # Check that the new tip is also downloadable.
        metadata_record = self._get_repository_metadata_by_changeset_revision(repository, new_changeset_revision)
        assert (
            metadata_record.downloadable
        ), f"The revision of {repository.name} that does not contain repository_dependencies.xml is not downloadable."
        # Verify that there are only two downloadable revisions.
        n_downloadable_revisions = len(self._db_repository(repository).downloadable_revisions)
        assert (
            n_downloadable_revisions == 2
        ), f"Repository {repository.name} has {n_downloadable_revisions} downloadable revisions, expected 2."

    def test_0030_create_bwa_package_repository(self):
        """Create and populate the bwa_package_0440 repository.

        We are at complex repository dependencies, step 1 - Create and populate bwa_package_0440 so that it has a valid
        tool dependency definition and an installable revision 0.
        """
        category = self.populator.get_category_with_name("Test 0440 Deleted Dependency Definitions")
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        strings_displayed = ["Repository <b>bwa_package_0440</b> has been created"]
        repository = self.get_or_create_repository(
            name=bwa_package_repository_name,
            description=bwa_package_repository_description,
            long_description=bwa_package_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=strings_displayed,
        )
        self.add_file_to_repository(repository, "bwa/complex/tool_dependencies.xml")

    def test_0035_create_bwa_base_repository(self):
        """Create and populate the bwa_base_0440 repository.

        We are at complex repository dependencies, step 2 - Create and populate bwa_base_0440 so that it has an installable revision 0.
        This repository should contain a tool with a defined dependency that will be satisfied by the tool dependency defined in bwa_package_0440.
        """
        category = self.populator.get_category_with_name("Test 0440 Deleted Dependency Definitions")
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        strings_displayed = ["Repository <b>bwa_base_0440</b> has been created"]
        repository = self.get_or_create_repository(
            name=bwa_base_repository_name,
            description=bwa_base_repository_description,
            long_description=bwa_base_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=strings_displayed,
        )
        self.commit_tar_to_repository(
            repository,
            "bwa/complex/bwa_base.tar",
            commit_message="Uploaded BWA nucleotide space mapping tool tarball.",
        )

    def test_0040_create_dependency_on_bwa_package_repository(self):
        """Create a complex repository dependency on bwa_package_0440 and upload it to bwa_tool_0440.

        We are at complex repository dependencies, step 3 - Add a valid complex repository dependency tool_dependencies.xml to
        bwa_base_0440 that points to the installable revision 0 of bwa_package_0440.
        """
        bwa_package_repository = self._get_repository_by_name_and_owner(
            bwa_package_repository_name, common.test_user_1_name
        )
        bwa_base_repository = self._get_repository_by_name_and_owner(bwa_base_repository_name, common.test_user_1_name)
        dependency_path = self.generate_temp_path("test_0440", additional_paths=["complex"])
        changeset_revision = self.get_repository_tip(bwa_package_repository)
        bwa_tuple = (self.url, bwa_package_repository.name, bwa_package_repository.owner, changeset_revision)
        self.create_repository_dependency(
            repository=bwa_base_repository,
            repository_tuples=[bwa_tuple],
            filepath=dependency_path,
            prior_installation_required=True,
            complex=True,
            package="bwa",
            version="0.5.9",
        )

    def test_0045_verify_dependency_metadata(self):
        """Verify that uploading the dependency moved metadata to the tip.

        We are at complex repository dependencies, step 4 - Make sure that bwa_base_0440 installable revision is now revision 1
        instead of revision 0.
        """
        repository = self._get_repository_by_name_and_owner(bwa_base_repository_name, common.test_user_1_name)
        tip = self.get_repository_tip(repository)
        metadata_record = self._get_repository_metadata_by_changeset_revision(repository, tip)
        # Make sure that the new tip is now downloadable, and that there are no other downloadable revisions.
        assert metadata_record.downloadable, "Tip is not downloadable."
        n_downloadable_revisions = len(self._db_repository(repository).downloadable_revisions)
        assert (
            n_downloadable_revisions == 1
        ), f"Repository {repository.name} has {n_downloadable_revisions} downloadable revisions, expected 1."

    def test_0050_delete_complex_repository_dependency(self):
        """Delete the tool_dependencies.xml from bwa_base_0440.

        We are at complex repository dependencies, step 5 - Delete tool_dependencies.xml from bwa_base_0440,
        and make sure bwa_base_0440 now has two installable revisions: 1 and 2
        """
        repository = self._get_repository_by_name_and_owner(bwa_base_repository_name, common.test_user_1_name)
        # Record the current tip, so we can verify that it's still a downloadable revision after tool_dependencies.xml
        # is deleted and a new downloadable revision is created.
        old_changeset_revision = self.get_repository_tip(repository)
        self.delete_files_from_repository(repository, filenames=["tool_dependencies.xml"])
        new_changeset_revision = self.get_repository_tip(repository)
        # Check that the old changeset revision is still downloadable.
        metadata_record = self._get_repository_metadata_by_changeset_revision(repository, old_changeset_revision)
        assert (
            metadata_record.downloadable
        ), f"The revision of {repository.name} that contains tool_dependencies.xml is no longer downloadable."
        # Check that the new tip is also downloadable.
        metadata_record = self._get_repository_metadata_by_changeset_revision(repository, new_changeset_revision)
        assert (
            metadata_record.downloadable
        ), f"The revision of {repository.name} that does not contain tool_dependencies.xml is not downloadable."
        # Verify that there are only two downloadable revisions.
        n_downloadable_revisions = len(self._db_repository(repository).downloadable_revisions)
        assert (
            n_downloadable_revisions == 2
        ), f"Repository {repository.name} has {n_downloadable_revisions} downloadable revisions, expected 2."

    def test_0055_create_bwa_tool_dependency_repository(self):
        """Create and populate the bwa_tool_dependency_0440 repository.

        We are at tool dependencies, step 1 - Create and populate bwa_tool_dependency_0440 so that it has a valid tool
        dependency definition and an installable revision 0.
        """
        category = self.populator.get_category_with_name("Test 0440 Deleted Dependency Definitions")
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        strings_displayed = ["Repository <b>bwa_tool_dependency_0440</b> has been created"]
        repository = self.get_or_create_repository(
            name=bwa_tool_dependency_repository_name,
            description=bwa_tool_dependency_repository_description,
            long_description=bwa_tool_dependency_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=strings_displayed,
        )
        self.add_file_to_repository(repository, "bwa/complex/tool_dependencies.xml")

    def test_0060_delete_bwa_tool_dependency_definition(self):
        """Delete the tool_dependencies.xml file from bwa_tool_dependency_0440.

        We are at tool dependencies, step 2 - Delete tool_dependencies.xml from bwa_tool_dependency_0440.
        Make sure bwa_tool_dependency_0440 still has a downloadable changeset revision at the old tip.
        """
        repository = self._get_repository_by_name_and_owner(
            bwa_tool_dependency_repository_name, common.test_user_1_name
        )
        # Record the current tip, so we can verify that it's still a downloadable revision after repository_dependencies.xml
        # is deleted and a new downloadable revision is created.
        old_changeset_revision = self.get_repository_tip(repository)
        self.delete_files_from_repository(repository, filenames=["tool_dependencies.xml"])
        new_changeset_revision = self.get_repository_tip(repository)
        assert old_changeset_revision != new_changeset_revision
        # Check that the old changeset revision is still downloadable.
        metadata_record = self._get_repository_metadata_by_changeset_revision(repository, old_changeset_revision)
        assert (
            metadata_record.downloadable
        ), f"The revision of {repository.name} that contains tool_dependencies.xml is no longer downloadable."
        # Check that the new tip does not have a metadata revision.
        metadata_record = self._get_repository_metadata_by_changeset_revision(repository, new_changeset_revision)
        # If a changeset revision does not have metadata, the above method will return None.
        assert (
            metadata_record is None
        ), f"The tip revision of {repository.name} should not have metadata, but metadata was found."
        # Verify that the new changeset revision is not downloadable.
        n_downloadable_revisions = len(self._db_repository(repository).downloadable_revisions)
        assert (
            n_downloadable_revisions == 1
        ), f"Repository {repository.name} has {n_downloadable_revisions} downloadable revisions, expected 1."

    def test_0065_reupload_bwa_tool_dependency_definition(self):
        """Reupload the tool_dependencies.xml file to bwa_tool_dependency_0440.

        We are at tool dependencies, step 3 - Add the same tool_dependencies.xml file to bwa_tool_dependency_0440, and make sure
        that bwa_tool_dependency_0440 still has a single installable revision 0.
        """
        repository = self._get_repository_by_name_and_owner(
            bwa_tool_dependency_repository_name, common.test_user_1_name
        )
        # Record the current tip, so we can verify that it's still not a downloadable revision after tool_dependencies.xml
        # is re-uploaded and a new downloadable revision is created.
        old_changeset_revision = self.get_repository_tip(repository)
        self.add_file_to_repository(repository, "bwa/complex/tool_dependencies.xml")
        new_changeset_revision = self.get_repository_tip(repository)
        # Check that the old changeset revision is still downloadable.
        metadata_record = self._get_repository_metadata_by_changeset_revision(repository, old_changeset_revision)
        assert (
            metadata_record is None
        ), f"The revision of {repository.name} that does not contain tool_dependencies.xml should not be downloadable, but is."
        # Check that the new tip is also downloadable.
        metadata_record = self._get_repository_metadata_by_changeset_revision(repository, new_changeset_revision)
        assert (
            metadata_record.downloadable
        ), f"The revision of {repository.name} that contains tool_dependencies.xml is not downloadable."
        # Verify that there are only two downloadable revisions.
        n_downloadable_revisions = len(self._db_repository(repository).downloadable_revisions)
        assert (
            n_downloadable_revisions == 1
        ), f"Repository {repository.name} has {n_downloadable_revisions} downloadable revisions, expected 1."

    def _get_repository_metadata_by_changeset_revision(self, repository: Repository, changeset: str):
        return self.get_repository_metadata_by_changeset_revision(self._db_repository(repository).id, changeset)
