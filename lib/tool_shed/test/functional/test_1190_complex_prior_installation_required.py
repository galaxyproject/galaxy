import os

from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

matplotlib_repository_name = "package_matplotlib_1_2_0170"
matplotlib_repository_description = (
    "Contains a tool dependency definition that downloads and compiles version 1.2.x of the python matplotlib package."
)
matplotlib_repository_long_description = (
    "This repository is intended to be defined as a complex repository dependency within a separate repository."
)

numpy_repository_name = "package_numpy_1_7_0170"
numpy_repository_description = (
    "Contains a tool dependency definition that downloads and compiles version 1.7 of the python numpy package."
)
numpy_repository_long_description = (
    "This repository is intended to be defined as a complex repository dependency within a separate repository."
)

category_name = "Test 0170 Prior Installation Complex Dependencies"
category_description = "Test 0170 Prior Installation Complex Dependencies"

"""
1. Create and populate repositories package_matplotlib_1_2_0170 and package_numpy_1_7_0170.
2. Create a complex repository dependency on package_numpy_1_7_0170, and upload this to package_matplotlib_1_2_0170.
3. Verify that package_matplotlib_1_2_0170 now depends on package_numpy_1_7_0170, and that the inherited tool dependency displays correctly.
4. Install package_matplotlib_1_2_0170 with repository dependencies.
5. Verify that the prior_installation_required attribute resulted in package_numpy_1_7_0170 being installed first.
"""

running_standalone = False


class TestComplexPriorInstallation(ShedTwillTestCase):
    """Test features related to datatype converters."""

    requires_galaxy = True

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_matplotlib_repository(self):
        """Create and populate the package_matplotlib_1_2_0170 repository.

        This is step 1 - Create and populate repositories package_matplotlib_1_2_0170 and package_numpy_1_7_0170.
        """
        global running_standalone
        category = self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name=matplotlib_repository_name,
            description=matplotlib_repository_description,
            long_description=matplotlib_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        if self.repository_is_new(repository):
            running_standalone = True
            self.commit_tar_to_repository(
                repository,
                "package_matplotlib/package_matplotlib_1_2.tar",
                commit_message="Uploaded matplotlib tool dependency tarball.",
            )

    def test_0010_create_numpy_repository(self):
        """Create and populate the package_numpy_1_7_0170 repository.

        This is step 1 - Create and populate repositories package_matplotlib_1_2_0170 and package_numpy_1_7_0170.
        """
        global running_standalone
        category = self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        if running_standalone:
            repository = self.get_or_create_repository(
                name=numpy_repository_name,
                description=numpy_repository_description,
                long_description=numpy_repository_long_description,
                owner=common.test_user_1_name,
                category=category,
                strings_displayed=[],
            )
            self.commit_tar_to_repository(
                repository,
                "package_numpy/package_numpy_1_7.tar",
                commit_message="Uploaded numpy tool dependency tarball.",
            )

    def test_0015_create_complex_repository_dependency(self):
        """Create a dependency on package_numpy_1_7_0170.

        This is step 2 - Create a complex repository dependency on package_numpy_1_7_0170, and upload this to package_matplotlib_1_2_0170.
        package_matplotlib_1_2_0170 should depend on package_numpy_1_7_0170, with prior_installation_required
        set to True. When matplotlib is selected for installation, the result should be that numpy is compiled
        and installed first.
        """
        global running_standalone
        numpy_repository = self._get_repository_by_name_and_owner(numpy_repository_name, common.test_user_1_name)
        matplotlib_repository = self._get_repository_by_name_and_owner(
            matplotlib_repository_name, common.test_user_1_name
        )
        # Generate the new dependency XML. Normally, the create_repository_dependency method would be used for this, but
        # it replaces any existing tool or repository dependency XML file with the generated contents. This is undesirable
        # in this case, because matplotlib already has an additional tool dependency definition that we don't want to
        # overwrite.
        new_xml = '    <package name="numpy" version="1.7">\n'
        new_xml += '        <repository toolshed="%s" name="%s" owner="%s" changeset_revision="%s" prior_installation_required="True" />\n'
        new_xml += "    </package>\n"
        url = self.url
        name = numpy_repository.name
        owner = numpy_repository.owner
        if running_standalone:
            changeset_revision = self.get_repository_tip(numpy_repository)
            processed_xml = new_xml % (url, name, owner, changeset_revision)
            original_xml = open(self.get_filename("package_matplotlib/tool_dependencies.xml")).read()
            dependency_xml_path = self.generate_temp_path("test_0170", additional_paths=["matplotlib"])
            new_xml_file = os.path.join(dependency_xml_path, "tool_dependencies.xml")
            open(new_xml_file, "w").write(original_xml.replace("<!--NUMPY-->", processed_xml))
            self.add_file_to_repository(matplotlib_repository, dependency_xml_path, "tool_dependencies.xml")

    def test_0020_verify_generated_dependency(self):
        """Verify that matplotlib now has a package tool dependency and a complex repository dependency.

        This is step 3 - Verify that package_matplotlib_1_2_0170 now depends on
        package_numpy_1_7_0170, and that the inherited tool dependency displays correctly.
        'Inherited' in this case means that matplotlib should show a package tool dependency on numpy version 1.7, and a repository
        dependency on the latest revision of package_numpy_1_7_0170.
        """
        numpy_repository = self._get_repository_by_name_and_owner(numpy_repository_name, common.test_user_1_name)
        matplotlib_repository = self._get_repository_by_name_and_owner(
            matplotlib_repository_name, common.test_user_1_name
        )
        changeset_revision = self.get_repository_tip(numpy_repository)
        self.check_repository_dependency(matplotlib_repository, depends_on_repository=numpy_repository)
        if not self.is_v2:
            self.display_manage_repository_page(
                matplotlib_repository, strings_displayed=["numpy", "1.7", "package", changeset_revision]
            )

    def test_0025_install_matplotlib_repository(self):
        """Install the package_matplotlib_1_2_0170 repository.

        This is step 4 - Install package_matplotlib_1_2_0170 with repository dependencies.
        """
        matplotlib_repository = self._get_repository_by_name_and_owner(
            matplotlib_repository_name, common.test_user_1_name
        )
        preview_strings_displayed = ["package_matplotlib_1_2_0170", self.get_repository_tip(matplotlib_repository)]
        self._install_repository(
            matplotlib_repository_name,
            common.test_user_1_name,
            category_name,
            install_tool_dependencies=False,
            install_repository_dependencies=True,
            preview_strings_displayed=preview_strings_displayed,
        )

    def test_0030_verify_installation_order(self):
        """Verify that the numpy repository was installed before the matplotlib repository.

        This is step 5 - Verify that the prior_installation_required attribute resulted in package_numpy_1_7_0170 being installed first.
        In the previous step, package_matplotlib_1_2_0170 was selected for installation, but package_numpy_1_7_0170 had the
        prior_installation_required attribute set. Confirm that this resulted in package_numpy_1_7_0170 being installed before
        package_matplotlib_1_2_0170.
        """
        matplotlib_repository = self._get_installed_repository_by_name_owner(
            matplotlib_repository_name, common.test_user_1_name
        )
        numpy_repository = self._get_installed_repository_by_name_owner(numpy_repository_name, common.test_user_1_name)
        assert (
            matplotlib_repository.update_time > numpy_repository.update_time
        ), "Error: package_numpy_1_7_0170 shows a later update time than package_matplotlib_1_2_0170"
