"""Integration tests for user config options."""

from galaxy.exceptions import error_codes
from galaxy_test.driver import integration_util


class _BaseUserExposeIntegrationTestCase(integration_util.IntegrationTestCase):
    def original_user_ids(self):
        return [u["id"] for u in self.galaxy_interactor.get("users").json()]

    def new_users(self, original_ids):
        users = [u for u in self.galaxy_interactor.get("users").json() if u["id"] not in original_ids]
        return users


class TestDefaultUserExposeIntegration(_BaseUserExposeIntegrationTestCase):
    def test_defaults(self):
        original_user_ids = self.original_user_ids()
        self.galaxy_interactor.ensure_user_with_email("defaultuserexposetest@galaxyproject.org")
        new_users = self.new_users(original_user_ids)
        # If expose username or expose email isn't enabled - user indexing is
        # empty by default for non-admin users.
        assert len(new_users) == 0


class TestEmailUserExposeIntegration(_BaseUserExposeIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["expose_user_email"] = True

    def test_only_email_exposed(self):
        original_user_ids = self.original_user_ids()
        self.galaxy_interactor.ensure_user_with_email("emailuserexposetest@galaxyproject.org")
        new_users = self.new_users(original_user_ids)
        assert len(new_users) > 0
        user = new_users[0]
        assert "email" in user
        assert "username" not in user
        assert "last_password_change" not in user


class TestUsernameUserExposeIntegration(_BaseUserExposeIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["expose_user_name"] = True

    def test_only_username_exposed(self):
        original_user_ids = self.original_user_ids()
        self.galaxy_interactor.ensure_user_with_email("usernameuserexposetest@galaxyproject.org")
        new_users = self.new_users(original_user_ids)
        assert len(new_users) > 0
        user = new_users[0]
        assert "email" not in user
        assert "username" in user
        assert "last_password_change" not in user


class TestAccountInterfaceDisabledIntegration(integration_util.IntegrationTestCase):
    """``enable_account_interface: false`` must be enforced by the API, not just hidden in the UI."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_account_interface"] = False

    def _assert_config_does_not_allow(self, response):
        self._assert_status_code_is(response, 403)
        self._assert_error_code_is(response, error_codes.error_codes_by_name["CONFIG_DOES_NOT_ALLOW"])

    def test_set_information_rejected_for_non_admin(self):
        with self._different_user("accountiface-information@bx.psu.edu"):
            user_id = self._get("users/current").json()["id"]
            response = self._put(
                f"users/{user_id}/information/inputs",
                data={"username": "renamedviaapi", "email": "renamedviaapi@bx.psu.edu"},
                json=True,
            )
            self._assert_config_does_not_allow(response)
            current = self._get(f"users/{user_id}/information/inputs").json()
            assert current["email"] == "accountiface-information@bx.psu.edu"

    def test_set_password_rejected_for_non_admin(self):
        with self._different_user("accountiface-password@bx.psu.edu"):
            user_id = self._get("users/current").json()["id"]
            response = self._put(
                f"users/{user_id}/password/inputs",
                data={"current": "testpass", "password": "newtestpass", "confirm": "newtestpass"},
                json=True,
            )
            self._assert_config_does_not_allow(response)

    def test_update_identity_rejected_for_non_admin(self):
        with self._different_user("accountiface-update@bx.psu.edu"):
            user_id = self._get("users/current").json()["id"]
            response = self._put(f"users/{user_id}", data={"username": "renamedviaupdate"}, json=True)
            self._assert_config_does_not_allow(response)

    def test_update_email_rejected_for_non_admin(self):
        with self._different_user("accountiface-email@bx.psu.edu"):
            user_id = self._get("users/current").json()["id"]
            response = self._put(f"users/{user_id}", data={"email": "changedviaupdate@bx.psu.edu"}, json=True)
            self._assert_config_does_not_allow(response)
            assert self._get("users/current").json()["email"] == "accountiface-email@bx.psu.edu"

    def test_update_display_name_rejected_for_non_admin(self):
        with self._different_user("accountiface-displayname@bx.psu.edu"):
            user_id = self._get("users/current").json()["id"]
            response = self._put(f"users/{user_id}", data={"display_name": "Changed Via Update"}, json=True)
            self._assert_config_does_not_allow(response)
            assert self._get("users/current").json()["display_name"] is None

    def test_update_non_identity_preference_still_allowed_for_non_admin(self):
        # preferred_object_store_id is an operational preference rather than account data, so
        # disabling the account interface must not lock users out of it.
        with self._different_user("accountiface-objectstore@bx.psu.edu"):
            user_id = self._get("users/current").json()["id"]
            response = self._put(f"users/{user_id}", data={"preferred_object_store_id": None}, json=True)
            self._assert_status_code_is(response, 200)

    def test_delete_rejected_for_non_admin(self):
        with self._different_user("accountiface-delete@bx.psu.edu"):
            user_id = self._get("users/current").json()["id"]
            response = self._delete(f"users/{user_id}")
            self._assert_config_does_not_allow(response)
            assert not self._get(f"users/{user_id}").json()["deleted"]

    def test_admins_can_still_modify_accounts(self):
        user = self._setup_user("accountiface-admintarget@bx.psu.edu")
        response = self._put(
            f"users/{user['id']}/information/inputs",
            data={"username": "renamedbyadmin", "email": "renamedbyadmin@bx.psu.edu"},
            json=True,
            admin=True,
        )
        self._assert_status_code_is(response, 200)
        updated = self._get(f"users/{user['id']}/information/inputs", admin=True).json()
        assert updated["username"] == "renamedbyadmin"


class TestLocalAccountsDisabledIntegration(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["disable_local_accounts"] = True

    def _assert_config_does_not_allow(self, response):
        self._assert_status_code_is(response, 403)
        self._assert_error_code_is(response, error_codes.error_codes_by_name["CONFIG_DOES_NOT_ALLOW"])

    def test_update_email_rejected_for_non_admin(self):
        with self._different_user("localdisabled-update@bx.psu.edu"):
            user_id = self._get("users/current").json()["id"]
            response = self._put(f"users/{user_id}", data={"email": "claimed-update@bx.psu.edu"}, json=True)
            self._assert_config_does_not_allow(response)
            assert self._get("users/current").json()["email"] == "localdisabled-update@bx.psu.edu"

    def test_set_information_email_rejected_for_non_admin(self):
        with self._different_user("localdisabled-information@bx.psu.edu"):
            user_id = self._get("users/current").json()["id"]
            response = self._put(
                f"users/{user_id}/information/inputs", data={"email": "claimed-information@bx.psu.edu"}, json=True
            )
            self._assert_config_does_not_allow(response)
            assert self._get("users/current").json()["email"] == "localdisabled-information@bx.psu.edu"

    def test_update_display_name_still_allowed_for_non_admin(self):
        with self._different_user("localdisabled-displayname@bx.psu.edu"):
            user_id = self._get("users/current").json()["id"]
            response = self._put(f"users/{user_id}", data={"display_name": "Ada Lovelace"}, json=True)
            self._assert_status_code_is(response, 200)
            assert response.json()["display_name"] == "Ada Lovelace"

    def test_admins_can_still_change_email(self):
        user = self._setup_user("localdisabled-admintarget@bx.psu.edu")
        response = self._put(f"users/{user['id']}", data={"email": "changedbyadmin@bx.psu.edu"}, json=True, admin=True)
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "changedbyadmin@bx.psu.edu"
