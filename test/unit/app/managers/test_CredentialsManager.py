from galaxy.managers.credentials import (
    CredentialsManager,
    CredentialsModelsList,
)
from galaxy.model import User
from galaxy.schema.credentials import SOURCE_TYPE
from .base import BaseTestCase


class TestCredentialsManager(BaseTestCase):

    def set_up_managers(self):
        super().set_up_managers()
        self.credentials_manager = CredentialsManager(self.trans.sa_session)

    def test_user_credentials(self):
        user = self._create_test_user()
        user_id = user.id
        name = "ServiceA"
        version = "1.0"
        source_type: SOURCE_TYPE = "tool"
        source_id = "tool_id"
        source_version = "tool_version"
        user_credentials = self.credentials_manager.get_user_credentials(
            user_id, source_type, source_id, source_version
        )

        user_credentials_id = self.credentials_manager.add_user_credentials(
            user_credentials, user_id, source_type, source_id, source_version, name, version
        )

        group_name = "group1"

        user_credential_group_id = self.credentials_manager.add_group(user_credentials, user_credentials_id, group_name)

        variable_name = "var1"
        variable_value = "value1"
        self.credentials_manager.add_or_update_credential(
            user_credentials, user_credential_group_id, variable_name, variable_value
        )

        secret_name = "secret1"
        secret_value = "value1"
        self.credentials_manager.add_or_update_credential(
            user_credentials, user_credential_group_id, secret_name, secret_value, is_secret=True
        )

        self.credentials_manager.update_current_group(user_id, user_credentials_id, group_name)
        self.trans.sa_session.commit()

        user_credentials = self.credentials_manager.get_user_credentials(
            user_id, source_type, source_id, source_version, user_credential_group_id
        )
        for result_user_credentials, result_credentials_group, _ in user_credentials:
            assert result_user_credentials.id == user_credentials_id
            assert result_user_credentials.user_id == user_id
            assert result_user_credentials.name == name
            assert result_user_credentials.version == version
            assert result_user_credentials.source_type == source_type
            assert result_user_credentials.source_id == source_id
            assert result_user_credentials.source_version == source_version
            assert result_user_credentials.current_group_id == user_credential_group_id
            assert result_credentials_group.id == user_credential_group_id
            assert result_credentials_group.name == group_name
            assert result_credentials_group.user_credentials_id == user_credentials_id

        assert user_credentials[0][2].group_id == user_credential_group_id
        assert user_credentials[0][2].name == variable_name
        assert user_credentials[0][2].value == variable_value
        assert not user_credentials[0][2].is_secret
        assert user_credentials[0][2].is_set

        assert user_credentials[1][2].group_id == user_credential_group_id
        assert user_credentials[1][2].name == secret_name
        assert user_credentials[1][2].value is None
        assert user_credentials[1][2].is_secret
        assert user_credentials[1][2].is_set

        rows_to_delete: CredentialsModelsList = [
            result_user_credentials,
            result_credentials_group,
            user_credentials[0][2],
            user_credentials[1][2],
        ]
        self.credentials_manager.delete_rows(rows_to_delete)
        self.trans.sa_session.commit()

    def _create_test_user(self, username="user1") -> User:
        user_data = dict(email=f"{username}@user.email", username=username, password="password")
        user = self.user_manager.create(**user_data)
        return user
