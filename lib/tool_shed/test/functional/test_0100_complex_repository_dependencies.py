import logging
import os

from ..base import common
from ..base.api import skip_if_api_v2
from ..base.twilltestcase import ShedTwillTestCase

log = logging.getLogger(__name__)

bwa_base_repository_name = "bwa_base_repository_0100"
bwa_base_repository_description = "BWA Base"
bwa_base_repository_long_description = (
    "BWA tool that depends on bwa 0.5.9, with a complex repository dependency pointing at package_bwa_0_5_9_0100"
)

bwa_package_repository_name = "package_bwa_0_5_9_0100"
bwa_package_repository_description = "BWA Tool"
bwa_package_repository_long_description = "BWA repository with a package tool dependency defined for BWA 0.5.9."

category_name = "Test 0100 Complex Repository Dependencies"
category_description = "Test 0100 Complex Repository Dependencies"


class TestComplexRepositoryDependencies(ShedTwillTestCase):
    """Test features related to complex repository dependencies."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username, explicit_logout=True)

    def test_0005_create_bwa_package_repository(self):
        """Create and populate package_bwa_0_5_9_0100."""
        category = self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        # Create a repository named package_bwa_0_5_9_0100 owned by user1.
        repository = self.get_or_create_repository(
            name=bwa_package_repository_name,
            description=bwa_package_repository_description,
            long_description=bwa_package_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        self.add_file_to_repository(repository, "bwa/complex/tool_dependencies.xml")
        if not self.is_v2:
            # Visit the manage repository page for package_bwa_0_5_9_0100.
            self.display_manage_repository_page(
                repository, strings_displayed=["Tool dependencies", "will not be", "to this repository"]
            )

    def test_0010_create_bwa_base_repository(self):
        """Create and populate bwa_base_0100."""
        category = self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        # Create a repository named bwa_base_repository_0100 owned by user1.
        repository = self.get_or_create_repository(
            name=bwa_base_repository_name,
            description=bwa_base_repository_description,
            long_description=bwa_base_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        # Populate the repository named bwa_base_repository_0100 with a bwa_base tool archive.
        self.commit_tar_to_repository(
            repository,
            "bwa/complex/bwa_base.tar",
            commit_message="Uploaded bwa_base.tar with tool wrapper XML, but without tool dependency XML.",
        )

    def test_0015_generate_complex_repository_dependency_invalid_shed_url(self):
        """Generate and upload a complex repository definition that specifies an invalid tool shed URL."""
        dependency_path = self.generate_temp_path("test_0100", additional_paths=["complex", "invalid"])
        # The repository named bwa_base_repository_0100 is the dependent repository.
        base_repository = self._get_repository_by_name_and_owner(bwa_base_repository_name, common.test_user_1_name)
        # The repository named package_bwa_0_5_9_0100 is the required repository.
        tool_repository = self._get_repository_by_name_and_owner(bwa_package_repository_name, common.test_user_1_name)
        url = "http://http://this is not an url!"
        name = "package_bwa_0_5_9_0100"
        owner = "user1"
        changeset_revision = self.get_repository_tip(tool_repository)
        strings_displayed = ["Repository dependencies are currently supported only within the same tool shed"]
        # Populate the dependent repository named bwa_base_repository_0100 with an invalid tool_dependencies.xml file.
        repository_tuple = (url, name, owner, changeset_revision)
        self.create_repository_dependency(
            repository=base_repository,
            filepath=dependency_path,
            repository_tuples=[repository_tuple],
            strings_displayed=strings_displayed,
            complex=True,
            package="bwa",
            version="0.5.9",
        )

    def test_0020_generate_complex_repository_dependency_invalid_repository_name(self):
        """Generate and upload a complex repository definition that specifies an invalid repository name."""
        dependency_path = self.generate_temp_path("test_0100", additional_paths=["complex", "invalid"])
        # The base_repository named bwa_base_repository_0100 is the dependent repository.
        base_repository = self._get_repository_by_name_and_owner(bwa_base_repository_name, common.test_user_1_name)
        # The repository named package_bwa_0_5_9_0100 is the required repository.
        tool_repository = self._get_repository_by_name_and_owner(bwa_package_repository_name, common.test_user_1_name)
        url = self.url
        name = "invalid_repository!?"
        owner = "user1"
        changeset_revision = self.get_repository_tip(tool_repository)
        strings_displayed = ["because the name is invalid"]
        # Populate the dependent base_repository named package_bwa_0_5_9_0100 with an invalid tool_dependencies.xml file.
        repository_tuple = (url, name, owner, changeset_revision)
        self.create_repository_dependency(
            repository=base_repository,
            filepath=dependency_path,
            repository_tuples=[repository_tuple],
            strings_displayed=strings_displayed,
            complex=True,
            package="bwa",
            version="0.5.9",
        )

    def test_0025_generate_complex_repository_dependency_invalid_owner_name(self):
        """Generate and upload a complex repository definition that specifies an invalid owner."""
        dependency_path = self.generate_temp_path("test_0100", additional_paths=["complex", "invalid"])
        # The base_repository named bwa_base_repository_0100 is the dependent repository.
        base_repository = self._get_repository_by_name_and_owner(bwa_base_repository_name, common.test_user_1_name)
        # The repository named package_bwa_0_5_9_0100 is the required repository.
        tool_repository = self._get_repository_by_name_and_owner(bwa_package_repository_name, common.test_user_1_name)
        url = self.url
        name = "package_bwa_0_5_9_0100"
        owner = "invalid_owner!?"
        changeset_revision = self.get_repository_tip(tool_repository)
        strings_displayed = ["because the owner is invalid."]
        repository_tuple = (url, name, owner, changeset_revision)
        self.create_repository_dependency(
            repository=base_repository,
            filepath=dependency_path,
            repository_tuples=[repository_tuple],
            strings_displayed=strings_displayed,
            complex=True,
            package="bwa",
            version="0.5.9",
        )

    def test_0030_generate_complex_repository_dependency_invalid_changeset_revision(self):
        """Generate and upload a complex repository definition that specifies an invalid changeset revision."""
        dependency_path = self.generate_temp_path("test_0100", additional_paths=["complex", "invalid"])
        # The base_repository named bwa_base_repository_0100 is the dependent repository.
        base_repository = self._get_repository_by_name_and_owner(bwa_base_repository_name, common.test_user_1_name)
        # The repository named package_bwa_0_5_9_0100 is the required repository.
        url = self.url
        name = "package_bwa_0_5_9_0100"
        owner = "user1"
        changeset_revision = "1234abcd"
        strings_displayed = ["because the changeset revision is invalid."]
        repository_tuple = (url, name, owner, changeset_revision)
        self.create_repository_dependency(
            repository=base_repository,
            filepath=dependency_path,
            repository_tuples=[repository_tuple],
            strings_displayed=strings_displayed,
            complex=True,
            package="bwa",
            version="0.5.9",
        )

    def test_0035_generate_complex_repository_dependency(self):
        """Generate and upload a valid tool_dependencies.xml file that specifies package_bwa_0_5_9_0100."""
        # The base_repository named bwa_base_repository_0100 is the dependent repository.
        base_repository = self._get_repository_by_name_and_owner(bwa_base_repository_name, common.test_user_1_name)
        # The repository named package_bwa_0_5_9_0100 is the required repository.
        tool_repository = self._get_repository_by_name_and_owner(bwa_package_repository_name, common.test_user_1_name)
        dependency_path = self.generate_temp_path("test_0100", additional_paths=["complex"])
        url = self.url
        name = "package_bwa_0_5_9_0100"
        owner = "user1"
        changeset_revision = self.get_repository_tip(tool_repository)
        repository_tuple = (url, name, owner, changeset_revision)
        self.create_repository_dependency(
            repository=base_repository,
            filepath=dependency_path,
            repository_tuples=[repository_tuple],
            complex=True,
            package="bwa",
            version="0.5.9",
        )
        self.check_repository_dependency(base_repository, depends_on_repository=tool_repository)
        if not self.is_v2:
            self.display_manage_repository_page(
                base_repository, strings_displayed=["bwa", "0.5.9", "package", changeset_revision]
            )

    @skip_if_api_v2
    def test_0040_generate_tool_dependency(self):
        """Generate and upload a new tool_dependencies.xml file that specifies an arbitrary file on the filesystem, and verify that bwa_base depends on the new changeset revision."""
        # The base_repository named bwa_base_repository_0100 is the dependent repository.
        base_repository = self._get_repository_by_name_and_owner(bwa_base_repository_name, common.test_user_1_name)
        # The repository named package_bwa_0_5_9_0100 is the required repository.
        tool_repository = self._get_repository_by_name_and_owner(bwa_package_repository_name, common.test_user_1_name)
        previous_changeset = self.get_repository_tip(tool_repository)
        old_tool_dependency = self.get_filename(os.path.join("bwa", "complex", "readme", "tool_dependencies.xml"))
        new_tool_dependency_path = self.generate_temp_path("test_1100", additional_paths=["tool_dependency"])
        xml_filename = os.path.abspath(os.path.join(new_tool_dependency_path, "tool_dependencies.xml"))
        # Generate a tool_dependencies.xml file that points to an arbitrary file in the local filesystem.
        open(xml_filename, "w").write(
            open(old_tool_dependency).read().replace("__PATH__", self.get_filename("bwa/complex"))
        )
        self.add_file_to_repository(tool_repository, xml_filename, "tool_dependencies.xml")
        # Verify that the dependency display has been updated as a result of the new tool_dependencies.xml file.
        repository_tip = self.get_repository_tip(tool_repository)
        strings_displayed = ["bwa", "0.5.9", "package"]
        strings_displayed.append(repository_tip)
        strings_not_displayed = [previous_changeset]
        self.display_manage_repository_page(
            tool_repository, strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed
        )
        # Visit the manage page of the package_bwa_0_5_9_0100 to confirm the valid tool dependency definition.
        self.display_manage_repository_page(
            tool_repository, strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed
        )
        # Visit the manage page of the bwa_base_repository_0100 to confirm the valid tool dependency definition
        # and the updated changeset revision (updated tip) of the package_bwa_0_5_9_0100 repository is displayed
        # as the required repository revision.  The original revision defined in the previously uploaded
        # tool_dependencies.xml file will be updated.
        self.display_manage_repository_page(
            base_repository, strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed
        )
