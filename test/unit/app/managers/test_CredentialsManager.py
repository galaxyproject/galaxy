from typing import (
    List,
    Tuple,
)

from galaxy.managers.credentials import CredentialsManager
from galaxy.model import (
    CredentialsGroup,
    Secret,
    User,
    UserCredentials,
    Variable,
)
from galaxy.schema.credentials import (
    CredentialsModelList,
    SOURCE_TYPE,
)
from .base import BaseTestCase


class TestCredentialsManager(BaseTestCase):

    def set_up_managers(self):
        super().set_up_managers()
        self.credentials_manager = CredentialsManager(self.trans.sa_session)

    def test_user_credentials(self):
        user = self._create_test_user()
        user_id = user.id
        reference = "ref1"
        source_type: SOURCE_TYPE = "tool"
        source_id = "tool_id"
        user_credentials: List[Tuple[UserCredentials, CredentialsGroup]] = []

        user_credentials_id = self.credentials_manager.add_user_credentials(
            user_credentials, user_id, reference, source_type, source_id
        )

        group_name = "group1"

        user_credential_group_id = self.credentials_manager.add_group(
            user_credentials, user_credentials_id, group_name, reference
        )

        variable_name = "var1"
        variable_value = "value1"
        variables: List[Variable] = []

        secret_name = "secret1"
        secret_value = "value1"
        secrets: List[Secret] = []

        self.credentials_manager.add_variable(variables, user_credential_group_id, variable_name, variable_value)
        self.credentials_manager.add_secret(secrets, user_credential_group_id, secret_name, secret_value)
        self.credentials_manager.update_current_group(user_id, user_credentials_id, group_name)
        self.credentials_manager.commit_session()

        result_user_credentials, result_credentials_group = self.credentials_manager.get_user_credentials(
            user_id, source_type, source_id, user_credentials_id, user_credential_group_id
        )[0]
        assert result_user_credentials.id == user_credentials_id
        assert result_user_credentials.user_id == user_id
        assert result_user_credentials.reference == reference
        assert result_user_credentials.source_type == source_type
        assert result_user_credentials.source_id == source_id
        assert result_user_credentials.current_group_id == user_credential_group_id
        assert result_credentials_group.id == user_credential_group_id
        assert result_credentials_group.name == group_name
        assert result_credentials_group.user_credentials_id == user_credentials_id

        variables, secrets = self.credentials_manager.fetch_credentials(user_credential_group_id)
        assert variables[0].user_credential_group_id == user_credential_group_id
        assert variables[0].name == variable_name
        assert variables[0].value == variable_value
        assert secrets[0].user_credential_group_id == user_credential_group_id
        assert secrets[0].name == secret_name
        assert secrets[0].already_set

        rows_to_delete: CredentialsModelList = [result_user_credentials, result_credentials_group, *variables, *secrets]
        self.credentials_manager.delete_rows(rows_to_delete)
        self.credentials_manager.commit_session()

    def _create_test_user(self, username="user1") -> User:
        user_data = dict(email=f"{username}@user.email", username=username, password="password")
        user = self.user_manager.create(**user_data)
        return user
