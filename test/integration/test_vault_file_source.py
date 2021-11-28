import os
import tempfile

from galaxy.security.vault import UserVaultWrapper
from galaxy_test.base import api_asserts
from galaxy_test.driver import integration_util


SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_VAULT_CONF = os.path.join(SCRIPT_DIRECTORY, "file_sources_conf_vault.yml")
VAULT_CONF = os.path.join(SCRIPT_DIRECTORY, "vault_conf.yml")


class VaultFileSourceIntegrationTestCase(integration_util.IntegrationTestCase):
    USER_1_APP_VAULT_ENTRY = "randomvaultuser1@universe.com"
    USER_2_APP_VAULT_ENTRY = "randomvaultuser2@universe.com"

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["file_sources_config_file"] = FILE_SOURCES_VAULT_CONF
        config["vault_config_file"] = VAULT_CONF
        config["user_library_import_symlink_allowlist"] = os.path.realpath(tempfile.mkdtemp())

    def test_vault_secret_per_user_in_file_source(self):
        """
        This file source performs a user vault lookup. The secret stored for the first user is a
        valid path and should succeed, while the second user's stored secret should fail.
        """
        with self._different_user(email=self.USER_1_APP_VAULT_ENTRY):
            app = self._app
            user = app.model.context.query(app.model.User).filter(
                app.model.User.email == self.USER_1_APP_VAULT_ENTRY).first()
            user_vault = UserVaultWrapper(self._app.vault, user)
            # use a valid symlink path so the posix list succeeds
            user_vault.write_secret('posix/root_path', app.config.user_library_import_symlink_allowlist[0])

            data = {"target": "gxfiles://test_user_vault"}
            list_response = self.galaxy_interactor.get("remote_files", data)
            api_asserts.assert_status_code_is_ok(list_response)
            remote_files = list_response.json()
            print(remote_files)

        with self._different_user(email=self.USER_2_APP_VAULT_ENTRY):
            app = self._app
            user = app.model.context.query(app.model.User).filter(
                app.model.User.email == self.USER_2_APP_VAULT_ENTRY).first()
            user_vault = UserVaultWrapper(self._app.vault, user)
            # use an invalid symlink path so the posix list fails
            user_vault.write_secret('posix/root_path', '/invalid/root')

            data = {"target": "gxfiles://test_user_vault"}
            list_response = self.galaxy_interactor.get("remote_files", data)
            api_asserts.assert_status_code_is(list_response, 404)

    def test_vault_secret_per_app_in_file_source(self):
        """
        This file source performs an app level vault lookup. Although the secret stored for the first user is a
        valid path and the second user's stored secret is invalid, we are performing an app level lookup
        which should succeed for both users.
        """
        # write app level secret
        app = self._app
        # use a valid symlink path so the posix list succeeds
        app.vault.write_secret('posix/root_path', app.config.user_library_import_symlink_allowlist[0])

        with self._different_user(email=self.USER_1_APP_VAULT_ENTRY):
            user = app.model.context.query(app.model.User).filter(
                app.model.User.email == self.USER_1_APP_VAULT_ENTRY).first()
            user_vault = UserVaultWrapper(self._app.vault, user)
            # use a valid symlink path so the posix list succeeds
            user_vault.write_secret('posix/root_path', app.config.user_library_import_symlink_allowlist[0])

            data = {"target": "gxfiles://test_app_vault"}
            list_response = self.galaxy_interactor.get("remote_files", data)
            api_asserts.assert_status_code_is_ok(list_response)
            remote_files = list_response.json()
            print(remote_files)

        with self._different_user(email=self.USER_2_APP_VAULT_ENTRY):
            user = app.model.context.query(app.model.User).filter(
                app.model.User.email == self.USER_2_APP_VAULT_ENTRY).first()
            user_vault = UserVaultWrapper(self._app.vault, user)
            # use an invalid symlink path so the posix list would fail if used
            user_vault.write_secret('posix/root_path', '/invalid/root')

            data = {"target": "gxfiles://test_app_vault"}
            list_response = self.galaxy_interactor.get("remote_files", data)
            api_asserts.assert_status_code_is_ok(list_response)
            remote_files = list_response.json()
            print(remote_files)
