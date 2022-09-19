"""Integration tests for user config options."""

from galaxy_test.driver import integration_util


class _BaseUserExposeIntegerationTestCase(integration_util.IntegrationTestCase):
    def original_user_ids(self):
        return [u["id"] for u in self.galaxy_interactor.get("users").json()]

    def new_users(self, original_ids):
        users = [u for u in self.galaxy_interactor.get("users").json() if u["id"] not in original_ids]
        return users


class DefaultUserExposeIntegrationTestCase(_BaseUserExposeIntegerationTestCase):
    def test_defaults(self):
        original_user_ids = self.original_user_ids()
        self.galaxy_interactor.ensure_user_with_email("defaultuserexposetest@galaxyproject.org")
        new_users = self.new_users(original_user_ids)
        # If expose username or expose email isn't enabled - user indexing is
        # empty by default for non-admin users.
        assert len(new_users) == 0


class EmailUserExposeIntegrationTestCase(_BaseUserExposeIntegerationTestCase):
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


class UsernameUserExposeIntegrationTestCase(_BaseUserExposeIntegerationTestCase):
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
