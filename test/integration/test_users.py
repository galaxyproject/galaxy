from typing import (
    ClassVar,
    Set,
)

from galaxy_test.driver import integration_util

USER_SUMMARY_KEYS: Set[str] = {"model_class", "id", "email", "username", "deleted", "active", "last_password_change"}


class UsersIntegrationCase(integration_util.IntegrationTestCase):
    expose_user_name: ClassVar[bool]
    expose_user_email: ClassVar[bool]
    expected_regular_user_list_count: ClassVar[int]
    expected_limited_user_keys: ClassVar[Set[str]]

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["expose_user_name"] = cls.expose_user_name
        config["expose_user_email"] = cls.expose_user_email

    def setUp(self):
        super().setUp()
        self._setup_users()

    def _setup_users(self):
        self.user = self._get("users/current").json()
        self.user2 = self._setup_user("user02@test.gx")
        self.user3 = self._setup_user("user03@test.gx")

    def test_admin_index(self):
        all_users_response = self._get("users", admin=True)
        self._assert_status_code_is(all_users_response, 200)
        all_users = all_users_response.json()
        assert len(all_users) == 3
        for user in all_users:
            self._assert_has_keys(user, *USER_SUMMARY_KEYS)

    def test_user_index(self):
        requesting_user_id = self.user["id"]
        all_users_response = self._get("users")
        self._assert_status_code_is(all_users_response, 200)
        all_users = all_users_response.json()
        assert len(all_users) == self.expected_regular_user_list_count

        unexpected_user_keys = USER_SUMMARY_KEYS - self.expected_limited_user_keys
        for user in all_users:
            if user["id"] == requesting_user_id:
                # Requesting users should be able to see their own information.
                self._assert_has_keys(user, *USER_SUMMARY_KEYS)
                continue
            # The user should be able to see other users information depending on the configuration.
            self._assert_has_keys(user, *self.expected_limited_user_keys)
            self._assert_not_has_keys(user, *unexpected_user_keys)


class TestExposeUsersIntegration(UsersIntegrationCase):
    expose_user_name = True
    expose_user_email = True

    # Since we allow to expose user information, all users are returned.
    expected_limited_user_keys = {"id", "username", "email"}
    expected_regular_user_list_count = 3


class TestExposeOnlyUserNameIntegration(UsersIntegrationCase):
    expose_user_name = True
    expose_user_email = False

    # When only username is exposed, only that field is returned in the user list.
    # Since we are exposing user information, all users are returned.
    expected_limited_user_keys = {"id", "username"}
    expected_regular_user_list_count = 3


class TestExposeOnlyUserEmailIntegration(UsersIntegrationCase):
    expose_user_name = False
    expose_user_email = True

    # When only email is exposed, only that field is returned in the user list.
    # Since we are exposing user information, all users are returned.
    expected_limited_user_keys = {"id", "email"}
    expected_regular_user_list_count = 3


class TestUnexposedUsersIntegration(UsersIntegrationCase):
    expose_user_name = False
    expose_user_email = False

    # Since no user information is exposed, only the current user should be returned.
    # And the current user has all fields, so no limited fields.
    expected_limited_user_keys = set()
    expected_regular_user_list_count = 1
