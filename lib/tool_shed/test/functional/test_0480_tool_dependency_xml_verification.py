import logging

from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

log = logging.getLogger(__name__)

category_name = "Test 0480 Tool dependency definition validation"
category_description = "Test script 0480 for validating tool dependency definitions."
repository_name = "package_invalid_tool_dependency_xml_1_0_0"
repository_description = "Contains a tool dependency definition that should return an error."
repository_long_description = "This repository is in the test suite 0480"

"""

1. Create a repository package_invalid_tool_dependency_xml_1_0_0
2. Upload a tool_dependencies.xml file to the repository with no <actions> tags around the <action> tags.
3. Verify error message is displayed.

"""


class TestDependencyDefinitionValidation(ShedTwillTestCase):
    """Test the tool shed's tool dependency XML validation."""

    def test_0000_initiate_users_and_category(self):
        """Create necessary user accounts and login as an admin user."""
        self.login(email=common.admin_email, username=common.admin_username)
        self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_2_email, username=common.test_user_2_name)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)

    def test_0005_create_tool_dependency_repository(self):
        """Create and populate package_invalid_tool_dependency_xml_1_0_0.

        This is step 1 - Create a repository package_invalid_tool_dependency_xml_1_0_0.

        Create a repository named package_invalid_tool_dependency_xml_1_0_0 that will contain only a single file named tool_dependencies.xml.
        """
        category = self.populator.get_category_with_name(category_name)
        repository = self.get_or_create_repository(
            name=repository_name,
            description=repository_description,
            long_description=repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        self.user_populator().setup_test_data_repo("0480", repository, assert_ok=False)

    def test_0010_populate_tool_dependency_repository(self):
        """Verify package_invalid_tool_dependency_xml_1_0_0.

        This is step 3 - Verify repository. The uploaded tool dependency XML should not have resulted in a new changeset.
        """
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        assert self.repository_is_new(
            repository
        ), "Uploading an incorrectly defined tool_dependencies.xml resulted in a changeset being generated."
