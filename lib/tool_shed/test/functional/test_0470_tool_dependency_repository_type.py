import logging

from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

log = logging.getLogger(__name__)

category_name = "Test 0470 Tool dependency repository type"
category_description = "Test script 0470 for changing repository types."
package_libx11_repository_name = "package_x11_client_1_5_proto_7_0_0470"
package_libx11_repository_description = (
    "Contains a tool dependency definition that provides the X11 client libraries and core protocol header files."
)
package_libx11_repository_long_description = (
    "Xlib is an X Window System protocol client library written in the C programming language."
)
package_emboss_repository_name = "package_emboss_5_0_0_0470"
package_emboss_repository_description = (
    "Contains a tool dependency definition that downloads and compiles version 5.0.0 of the EMBOSS tool suite."
)
package_emboss_repository_long_description = 'EMBOSS is "The European Molecular Biology Open Software Suite".'
datatypes_repository_name = "emboss_datatypes_0470"
datatypes_repository_description = "Galaxy applicable data formats used by Emboss tools."
datatypes_repository_long_description = (
    "Galaxy applicable data formats used by Emboss tools.  This repository contains no tools."
)
emboss_repository_name = "emboss_5_0470"
emboss_repository_description = "Galaxy wrappers for Emboss version 5.0.0 tools"
emboss_repository_long_description = "Galaxy wrappers for Emboss version 5.0.0 tools"

"""
1. Create and populate a repository named package_x11_client_1_5_proto_7_0 that contains only a single file named tool_dependencies.xml.
   Keep the repository type as the default "Unrestricted".

2. Create a repository named package_emboss_5_0_0 of type "Unrestricted" that has a repository dependency definition that defines the
   above package_x11_client_1_5_proto_7_0 repository. Upload the tool_dependencies.xml file such that it does not have a changeset_revision
   defined so it will get automatically populated.

3. Create a repository named emboss_5 of type "Unrestricted" that has a tool-dependencies.xml file defining a complex repository dependency
   on the package_emboss_5_0_0 repository above. Upload the tool_dependencies.xml file such that it does not have a change set_revision defined
   so it will get automatically populated.

4. Add a comment to the tool_dependencies.xml file to be uploaded to the package_x11_client_1_5_prot_7_0 repository, creating a new installable
   changeset revision at the repository tip.

5. Add a comment to the tool_dependencies.xml file for the package_emboss_5_0_0 repository, eliminating the change set_revision attribute so
   that it gets automatically populated when uploaded. After uploading the file, the package_emboss_5_0_0 repository should have 2
   installable changeset revisions.

6. Add a comment to the tool_dependencies.xml file in the emboss_5 repository, eliminating the changeset_revision attribute so that it gets
   automatically populated when uploaded. After uploading the file, the emboss5 repository should have 2 installable metadata revisions.

7. Change the repository type of the package_x11_client_1_5_proto_7_0 repository to be tool_dependency_definition.

8. Change the repository type of the package_emboss_5_0_0 repository to be tool_dependency_definition.

9. Reset metadata on the package_emboss_5_0_0 repository. It should now have only its tip as the installable revision.

10. Reset metadata on the emboss_5 repository. It should now have only its tip as the installable revision.
"""


class TestEnvironmentInheritance(ShedTwillTestCase):
    """Test referencing environment variables that were defined in a separate tool dependency."""

    def test_0000_initiate_users_and_category(self):
        """Create necessary user accounts and login as an admin user."""
        self.login(email=common.admin_email, username=common.admin_username)
        self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_2_email, username=common.test_user_2_name)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)

    def test_0005_create_libx11_repository(self):
        """Create and populate package_x11_client_1_5_proto_7_0_0470.

        This is step 1 - Create and populate a repository named package_x11_client_1_5_proto_7_0.

        Create and populate a repository named package_x11_client_1_5_proto_7_0 that contains only a single file named tool_dependencies.xml.
        Keep the repository type as the default "Unrestricted".
        """
        category = self.populator.get_category_with_name(category_name)
        repository = self.get_or_create_repository(
            name=package_libx11_repository_name,
            description=package_libx11_repository_description,
            long_description=package_libx11_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        # Upload the tool dependency definition to the package_x11_client_1_5_proto_7_0_0470 repository.
        self.user_populator().setup_test_data_repo("libx11_proto", repository, end=1)

    def test_0010_create_emboss_5_0_0_repository(self):
        """Create and populate package_emboss_5_0_0_0470.

        This is step 2 - Create a repository named package_emboss_5_0_0 of type "Unrestricted".

        Create a repository named package_emboss_5_0_0 of type "Unrestricted" that has a repository dependency definition that defines the
        above package_x11_client_1_5_proto_7_0 repository. Upload the tool_dependencues.xml file such that it does not have a changeset_revision
        defined so it will get automatically populated.
        """
        category = self.populator.get_category_with_name(category_name)
        repository = self.get_or_create_repository(
            name=package_emboss_repository_name,
            description=package_emboss_repository_description,
            long_description=package_emboss_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        # Upload the edited tool dependency definition to the package_emboss_5_0_0 repository.
        self.user_populator().setup_test_data_repo("package_emboss_5_0_0_0470", repository, end=1)

    def test_0015_create_emboss_5_repository(self):
        """Create and populate emboss_5_0470.

        This is step 3 - Create a repository named emboss_5 of type "Unrestricted".

        Create a repository named emboss_5 of type "Unrestricted" that has a tool-dependencies.xml file defining a complex repository dependency
        on the package_emboss_5_0_0 repository above. Upload the tool_dependencies.xml file such that it does not have a change set_revision defined
        so it will get automatically populated.
        """
        category = self.populator.get_category_with_name(category_name)
        repository = self.get_or_create_repository(
            name=emboss_repository_name,
            description=emboss_repository_description,
            long_description=emboss_repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        # Populate emboss_5 with tool and dependency definitions.
        self.user_populator().setup_test_data_repo("emboss_5_0470", repository, end=1)

    def test_0020_upload_updated_tool_dependency_to_package_x11(self):
        """Upload a new tool_dependencies.xml to package_x11_client_1_5_proto_7_0_0470.

        This is step 4 - Add a comment to the tool_dependencies.xml file to be uploaded to the package_x11_client_1_5_prot_7_0 repository, creating
        a new installable changeset revision at the repository tip.
        """
        package_x11_repository = self._get_repository_by_name_and_owner(
            package_libx11_repository_name, common.test_user_1_name
        )
        # Upload the tool dependency definition to the package_x11_client_1_5_proto_7_0_0470 repository.
        self.user_populator().setup_test_data_repo("libx11_proto", package_x11_repository, start=1, end=2)
        count = self._get_metadata_revision_count(package_x11_repository)
        assert (
            count == 1
        ), f"package_x11_client_1_5_proto_7_0_0470 has incorrect number of metadata revisions, expected 1 but found {count}"

    def test_0025_upload_updated_tool_dependency_to_package_emboss(self):
        """Upload a new tool_dependencies.xml to package_emboss_5_0_0_0470.

        This is step 5 - Add a comment to the tool_dependencies.xml file for the package_emboss_5_0_0 repository, eliminating
        the change set_revision attribute so that it gets automatically populated when uploaded. After uploading the file,
        the package_emboss_5_0_0 repository should have 2 installable changeset revisions.
        """
        package_emboss_repository = self._get_repository_by_name_and_owner(
            package_emboss_repository_name, common.test_user_1_name
        )
        # Populate package_emboss_5_0_0_0470 with updated tool dependency definition.
        self.user_populator().setup_test_data_repo(
            "package_emboss_5_0_0_0470", package_emboss_repository, start=1, end=2
        )
        count = self._get_metadata_revision_count(package_emboss_repository)
        assert (
            count == 2
        ), f"package_emboss_5_0_0_0470 has incorrect number of metadata revisions, expected 2 but found {count}"

    def test_0030_upload_updated_tool_dependency_to_emboss_5_repository(self):
        """Upload a new tool_dependencies.xml to emboss_5_0470.

        This is step 6 - Add a comment to the tool_dependencies.xml file in the emboss_5 repository, eliminating the
        changeset_revision attribute so that it gets automatically populated when uploaded. After uploading the file,
        the emboss5 repository should have 2 installable metadata revisions.
        """
        emboss_repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
        # Populate package_emboss_5_0_0_0470 with updated tool dependency definition.
        self.user_populator().setup_test_data_repo("emboss_5_0470", emboss_repository, start=1, end=2)
        count = self._get_metadata_revision_count(emboss_repository)
        assert count == 2, "package_emboss_5_0_0_0470 has incorrect number of metadata revisions"

    def test_0035_modify_package_x11_repository_type(self):
        """Set package_x11_client_1_5_proto_7_0 type tool_dependency_definition.

        This is step 7 - Change the repository type of the package_x11_client_1_5_proto_7_0 repository to be tool_dependency_definition.
        """
        package_x11_repository = self._get_repository_by_name_and_owner(
            package_libx11_repository_name, common.test_user_1_name
        )
        self.edit_repository_information(package_x11_repository, repository_type="tool_dependency_definition")

    def test_0040_modify_package_emboss_repository_type(self):
        """Set package_emboss_5_0_0 to type tool_dependency_definition.

        This is step 8 - Change the repository type of the package_emboss_5_0_0 repository to be tool_dependency_definition.
        """
        package_emboss_repository = self._get_repository_by_name_and_owner(
            package_emboss_repository_name, common.test_user_1_name
        )
        self.edit_repository_information(package_emboss_repository, repository_type="tool_dependency_definition")

    def test_0045_reset_repository_metadata(self):
        """Reset metadata on package_emboss_5_0_0_0470 and package_x11_client_1_5_proto_7_0.

        This is step 9 - Reset metadata on the package_emboss_5_0_0 and package_x11_client_1_5_proto_7_0 repositories. They should
        now have only their tip as the installable revision.
        """
        package_emboss_repository = self._get_repository_by_name_and_owner(
            package_emboss_repository_name, common.test_user_1_name
        )
        package_x11_repository = self._get_repository_by_name_and_owner(
            package_libx11_repository_name, common.test_user_1_name
        )
        self.reset_repository_metadata(package_emboss_repository)
        self.reset_repository_metadata(package_x11_repository)
        count = self._get_metadata_revision_count(package_emboss_repository)
        assert count == 1, f"Repository package_emboss_5_0_0 has {count} installable revisions, expected 1."
        count = self._get_metadata_revision_count(package_x11_repository)
        assert count == 1, f"Repository package_x11_client_1_5_proto_7_0 has {count} installable revisions, expected 1."

    def test_0050_reset_emboss_5_metadata(self):
        """Reset metadata on emboss_5.

        This is step 10 - Reset metadata on the emboss_5 repository. It should now have only its tip as the installable revision.
        """
        emboss_repository = self._get_repository_by_name_and_owner(emboss_repository_name, common.test_user_1_name)
        self.reset_repository_metadata(emboss_repository)
        count = self._get_metadata_revision_count(emboss_repository)
        assert count == 1, f"Repository emboss_5 has {count} installable revisions, expected 1."
