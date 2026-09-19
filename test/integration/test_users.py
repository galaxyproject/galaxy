import json
import os
import re
from typing import (
    ClassVar,
)

from galaxy_test.driver import integration_util

USER_SUMMARY_KEYS: set[str] = {"model_class", "id", "email", "username", "deleted", "active", "last_password_change"}


class UsersIntegrationCase(integration_util.IntegrationTestCase):
    expose_user_name: ClassVar[bool]
    expose_user_email: ClassVar[bool]
    expected_regular_user_list_count: ClassVar[int]
    expected_limited_user_keys: ClassVar[set[str]]

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


class TestAdminResendActivationEmail(integration_util.IntegrationTestCase):
    email_directory: ClassVar[str]

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.email_directory = cls._test_driver.mkdtemp()
        config["user_activation_on"] = True
        config["activation_grace_period"] = 3
        config["email_from"] = "galaxy-noreply@example.com"
        config["smtp_server"] = f"mock_emails_to_path://{cls.email_directory}/email.json"

    def test_email_change_deactivates_and_mails_the_new_address(self):
        old_email = "email-change-before@test.gx"
        new_email = "email-change-after@test.gx"
        user = self._setup_user(old_email)

        with self._different_user(email=old_email):
            response = self._put(f"users/{user['id']}", data={"email": new_email}, json=True)
            self._assert_status_code_is_ok(response)
            updated = response.json()

        assert updated["email"] == new_email

        # Changing the address has to re-verify it, otherwise activation is a
        # one-time gate that any later edit walks straight past. `active` is not on
        # DetailedUserModel, so it is read back from the index.
        listed = self._get("users", data={"f_email": new_email}, admin=True).json()
        assert [u for u in listed if u["email"] == new_email][0]["active"] is False

        with open(os.path.join(self.email_directory, "email.json")) as f:
            email = json.loads(f.read())
        assert email["to"] == new_email
        assert email["subject"] == "Galaxy Account Activation"

        # The private role is named for the email and is what dataset permissions
        # are granted against, so it has to follow the address.
        role_names = [role["name"] for role in self._get("roles", admin=True).json()]
        assert new_email in role_names
        assert old_email not in role_names

    def test_resend_activation_includes_qualified_link(self):
        user = self._setup_user("resend-activation@test.gx")
        response = self._post(f"users/{user['id']}/send_activation_email", admin=True)
        self._assert_status_code_is_ok(response)

        with open(os.path.join(self.email_directory, "email.json")) as f:
            email = json.loads(f.read())
        assert email["to"] == "resend-activation@test.gx"
        assert email["subject"] == "Galaxy Account Activation"
        match = re.search(r"(https?://[^/\s]+/user/activate\?[^\s]+)", email["body"])
        assert match, f"No qualified activation link found in email body:\n{email['body']}"
        link = match.group(1)
        assert "activation_token=" in link
        assert "email=" in link
