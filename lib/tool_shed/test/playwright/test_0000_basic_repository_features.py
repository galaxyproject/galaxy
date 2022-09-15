from tool_shed.test.base.twilltestcase import common
from ._framework import ShedPlaywrightTestCase


class TestBasicRepositoryFeatures(ShedPlaywrightTestCase):
    def test_0000_initiate_users(self):
        self._login(email=common.test_user_1_email, username=common.test_user_1_name)
        test_user_1 = self.test_db_util.get_user(common.test_user_1_email)
        assert (
            test_user_1 is not None
        ), f"Problem retrieving user with email {common.test_user_1_email} from the database"
        self.test_db_util.get_private_role(test_user_1)
        self._login(email=common.test_user_2_email, username=common.test_user_2_name)
        test_user_2 = self.test_db_util.get_user(common.test_user_2_email)
        assert (
            test_user_2 is not None
        ), f"Problem retrieving user with email {common.test_user_2_email} from the database"
        self.test_db_util.get_private_role(test_user_2)
        self._login(email=common.admin_email, username=common.admin_username)
        admin_user = self.test_db_util.get_user(common.admin_email)
        assert admin_user is not None, f"Problem retrieving user with email {common.admin_email} from the database"
        self.test_db_util.get_private_role(admin_user)

    def test_0005_create_repository_without_categories(self):
        """Verify that a repository cannot be created unless at least one category has been defined."""
        strings_displayed = ["No categories have been configured in this instance of the Galaxy Tool Shed"]
        self._visit_url("/repository/create_repository")
        self._check_for_strings(strings_displayed=strings_displayed, strings_not_displayed=[])

    def test_0010_create_categories(self):
        """Create categories for this test suite"""
        self._create_category(
            name="Test 0000 Basic Repository Features 1", description="Test 0000 Basic Repository Features 1"
        )
        self._create_category(
            name="Test 0000 Basic Repository Features 2", description="Test 0000 Basic Repository Features 2"
        )
