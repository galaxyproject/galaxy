from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

datatypes_repository_name = "blast_datatypes_0120"
datatypes_repository_description = "Galaxy applicable datatypes for BLAST"
datatypes_repository_long_description = "Galaxy datatypes for the BLAST top hit descriptons tool"

tool_repository_name = "blastxml_to_top_descr_0120"
tool_repository_description = "BLAST top hit descriptions"
tool_repository_long_description = "Make a table from BLAST XML"

"""
Tool shed side:

1) Create and populate blast_datatypes_0120.
1a) Check for appropriate strings.
2) Create and populate blastxml_to_top_descr_0120.
2a) Check for appropriate strings.
3) Upload repository_dependencies.xml to blastxml_to_top_descr_0120 that defines a relationship to blast_datatypes_0120.
3a) Check for appropriate strings.
Galaxy side:

1) Install blastxml_to_top_descr_0120, with repository dependencies.
1a) Check for appropriate strings in the installed blastxml_to_top_descr_0120 and blast_datatypes_0120 repositories.
"""

running_standalone = False


class TestInstallRepositoryMultipleOwners(ShedTwillTestCase):
    requires_galaxy = True

    def test_0000_initiate_users(self):
        """Create necessary user accounts and login as an admin user.

        Create all the user accounts that are needed for this test script to run independently of other tests.
        Previously created accounts will not be re-created.
        """
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.test_user_2_email, username=common.test_user_2_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_datatypes_repository(self):
        """Create and populate the blast_datatypes_0120 repository

        We are at step 1.
        Create and populate blast_datatypes.
        """
        category = self.create_category(name="Test 0120", description="Description of test 0120")
        self.login(email=common.test_user_2_email, username=common.test_user_2_name)
        strings_displayed = self.expect_repo_created_strings(datatypes_repository_name)
        repository = self.get_or_create_repository(
            name=datatypes_repository_name,
            description=datatypes_repository_description,
            long_description=datatypes_repository_long_description,
            owner=common.test_user_2_name,
            category=category,
            strings_displayed=strings_displayed,
        )
        if self.repository_is_new(repository):
            self.commit_tar_to_repository(
                repository,
                "blast/blast_datatypes.tar",
                commit_message="Uploaded blast_datatypes tarball.",
            )

    def test_0010_verify_datatypes_repository(self):
        """Verify the blast_datatypes_0120 repository.

        We are at step 1a.
        Check for appropriate strings, most importantly BlastXml, BlastNucDb, and BlastProtDb,
        the datatypes that are defined in datatypes_conf.xml.
        """
        repository = self._get_repository_by_name_and_owner(datatypes_repository_name, common.test_user_2_name)
        strings_displayed = [
            "BlastXml",
            "BlastNucDb",
            "BlastProtDb",
            "application/xml",
            "text/html",
            "blastxml",
            "blastdbn",
            "blastdbp",
        ]
        if not self.is_v2:
            self.display_manage_repository_page(repository, strings_displayed=strings_displayed)

    def test_0015_create_tool_repository(self):
        """Create and populate the blastxml_to_top_descr_0120 repository

        We are at step 2.
        Create and populate blastxml_to_top_descr_0120.
        """
        global running_standalone
        category = self.create_category(name="Test 0120", description="Description of test 0120")
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        strings_displayed = self.expect_repo_created_strings(tool_repository_name)
        repository = self.get_or_create_repository(
            name=tool_repository_name,
            description=tool_repository_description,
            long_description=tool_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=strings_displayed,
        )
        if self.repository_is_new(repository):
            running_standalone = True
            self.commit_tar_to_repository(
                repository,
                "blast/blastxml_to_top_descr.tar",
                commit_message="Uploaded blastxml_to_top_descr tarball.",
            )

    def test_0020_verify_tool_repository(self):
        """Verify the blastxml_to_top_descr_0120 repository.

        We are at step 2a.
        Check for appropriate strings, such as tool name, description, and version.
        """
        repository = self._get_repository_by_name_and_owner(tool_repository_name, common.test_user_1_name)
        strings_displayed = ["blastxml_to_top_descr_0120", "BLAST top hit descriptions", "Make a table from BLAST XML"]
        strings_displayed.extend(["0.0.1"])
        self.display_manage_repository_page(repository, strings_displayed=strings_displayed)

    def test_0025_create_repository_dependency(self):
        """Create a repository dependency on blast_datatypes_0120.

        We are at step 3.
        Create a simple repository dependency for blastxml_to_top_descr_0120 that defines a dependency on blast_datatypes_0120.
        """
        global running_standalone
        if running_standalone:
            datatypes_repository = self._get_repository_by_name_and_owner(
                datatypes_repository_name, common.test_user_2_name
            )
            tool_repository = self._get_repository_by_name_and_owner(tool_repository_name, common.test_user_1_name)
            dependency_xml_path = self.generate_temp_path("test_1120", additional_paths=["dependencies"])
            datatypes_tuple = (
                self.url,
                datatypes_repository.name,
                datatypes_repository.owner,
                self.get_repository_tip(datatypes_repository),
            )
            self.create_repository_dependency(
                repository=tool_repository, repository_tuples=[datatypes_tuple], filepath=dependency_xml_path
            )

    def test_0040_verify_repository_dependency(self):
        """Verify the created repository dependency.

        We are at step 3a.
        Check the newly created repository dependency to ensure that it was defined and displays correctly.
        """
        datatypes_repository = self._get_repository_by_name_and_owner(
            datatypes_repository_name, common.test_user_2_name
        )
        tool_repository = self._get_repository_by_name_and_owner(tool_repository_name, common.test_user_1_name)
        self.check_repository_dependency(tool_repository, datatypes_repository)

    def test_0045_install_blastxml_to_top_descr(self):
        """Install the blastxml_to_top_descr_0120 repository to Galaxy.

        We are at step 1, Galaxy side.
        Install blastxml_to_top_descr_0120 to Galaxy, with repository dependencies, so that the datatypes repository is also installed.
        """
        self._install_repository(
            name="blastxml_to_top_descr_0120",
            owner=common.test_user_1_name,
            category_name="Test 0120",
            install_repository_dependencies=True,
            new_tool_panel_section_label="Test 0120",
        )

    def test_0050_verify_repository_installation(self):
        """Verify installation of blastxml_to_top_descr_0120 and blast_datatypes_0120.

        We are at step 1a, Galaxy side.
        Check that the blastxml_to_top_descr_0120 and blast_datatypes_0120 repositories installed correctly, and that there
        are now new datatypes in the registry matching the ones defined in blast_datatypes_0120. Also check that
        blast_datatypes_0120 is labeled as an installed repository dependency of blastxml_to_top_descr_0120.
        """
        tool_repository = self._get_installed_repository_by_name_owner(tool_repository_name, common.test_user_1_name)
        self._assert_has_valid_tool_with_name("BLAST top hit")
        self._assert_repo_has_tool_with_id(tool_repository, "blastxml_to_top_descr")
