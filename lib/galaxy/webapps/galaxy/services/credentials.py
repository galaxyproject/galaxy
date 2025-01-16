from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from galaxy.exceptions import (
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.credentials import CredentialsManager
from galaxy.model import (
    CredentialsGroup,
    Secret,
    UserCredentials,
    Variable,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.credentials import (
    CreateSourceCredentialsPayload,
    SOURCE_TYPE,
    UserCredentialsListResponse,
    UserCredentialsResponse,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import FlexibleUserIdType
from galaxy.security.vault import UserVaultWrapper
from galaxy.structured_app import StructuredApp


class CredentialsService:
    """Service object shared by controllers for interacting with credentials."""

    def __init__(
        self,
        app: StructuredApp,
        credentials_manager: CredentialsManager,
    ) -> None:
        self._app = app
        self._credentials_manager = credentials_manager

    def list_user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
    ) -> UserCredentialsListResponse:
        """Lists all credentials the user has provided (credentials themselves are not included)."""
        return self._list_user_credentials(trans, user_id, source_type, source_id)

    def provide_credential(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        payload: CreateSourceCredentialsPayload,
    ) -> UserCredentialsListResponse:
        """Allows users to provide credentials for a group of secrets and variables."""
        self._create_or_update_credentials(trans, user_id, payload)
        return self._list_user_credentials(trans, user_id, payload.source_type, payload.source_id)

    def delete_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        user_credentials_id: Optional[DecodedDatabaseIdField] = None,
        group_id: Optional[DecodedDatabaseIdField] = None,
    ) -> None:
        """Deletes a specific credential group or all credentials for a specific service."""
        db_user_credentials = self._credentials_manager.get_user_credentials(
            trans, user_id, user_credentials_id=user_credentials_id, group_id=group_id
        )
        if not db_user_credentials:
            raise ObjectNotFound("No credentials found.")
        rows_to_delete: List[Union[UserCredentials, CredentialsGroup, Variable, Secret]] = []
        for uc, credentials_group in db_user_credentials:
            if not group_id:
                rows_to_delete.append(uc)
            else:
                if credentials_group.name == "default":
                    raise RequestParameterInvalidException("Cannot delete the default group.")
                if credentials_group.id == uc.current_group_id:
                    self._credentials_manager.update_current_group(trans, uc.id, "default")
            variables, secrets = self._credentials_manager.fetch_credentials(trans.sa_session, credentials_group.id)
            rows_to_delete.extend([credentials_group, *variables, *secrets])
        self._credentials_manager.delete_rows(trans.sa_session, rows_to_delete)

    def _list_user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
    ) -> UserCredentialsListResponse:
        db_user_credentials = self._credentials_manager.get_user_credentials(trans, user_id, source_type, source_id)
        credentials_dict = self._map_user_credentials(db_user_credentials)
        for user_credentials, credentials_group in db_user_credentials:
            variables, secrets = self._credentials_manager.fetch_credentials(trans.sa_session, credentials_group.id)
            group = credentials_dict[user_credentials.id]["groups"].get(credentials_group.name, {})
            group["variables"].extend(
                {"id": variable.id, "name": variable.name, "value": variable.value} for variable in variables
            )
            group["secrets"].extend(
                {"id": secret.id, "name": secret.name, "already_set": secret.already_set} for secret in secrets
            )

        return UserCredentialsListResponse(root=[UserCredentialsResponse(**cred) for cred in credentials_dict.values()])

    def _map_user_credentials(
        self,
        db_user_credentials: List[Tuple[UserCredentials, CredentialsGroup]],
    ) -> Dict[int, Dict[str, Any]]:
        user_credentials_dict: Dict[int, Dict[str, Any]] = {}
        group_name = {group.id: group.name for _, group in db_user_credentials}
        for user_credentials, credentials_group in db_user_credentials:
            cred_id = user_credentials.id
            user_credentials_dict.setdefault(
                cred_id,
                {
                    "user_id": user_credentials.user_id,
                    "id": cred_id,
                    "reference": user_credentials.reference,
                    "source_type": user_credentials.source_type,
                    "source_id": user_credentials.source_id,
                    "current_group_id": user_credentials.current_group_id,
                    "current_group_name": group_name[user_credentials.current_group_id],
                    "groups": {},
                },
            )

            user_credentials_dict[cred_id]["groups"].setdefault(
                credentials_group.name,
                {
                    "id": credentials_group.id,
                    "name": credentials_group.name,
                    "variables": [],
                    "secrets": [],
                },
            )

        return user_credentials_dict

    def _create_or_update_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        payload: CreateSourceCredentialsPayload,
    ) -> None:
        session = trans.sa_session
        source_type, source_id = payload.source_type, payload.source_id
        db_user_credentials = self._credentials_manager.get_user_credentials(trans, user_id, source_type, source_id)
        for service_payload in payload.credentials:
            reference = service_payload.reference
            current_group_name = service_payload.current_group
            if not current_group_name:
                current_group_name = "default"
            user_credentials_id = self._credentials_manager.add_user_credentials(
                session, db_user_credentials, trans.user.id, reference, source_type, source_id
            )
            for group in service_payload.groups:
                group_name = group.name
                user_credential_group_id = self._credentials_manager.add_group(
                    session, db_user_credentials, user_credentials_id, group_name, reference
                )
                variables, secrets = self._credentials_manager.fetch_credentials(session, user_credential_group_id)
                user_vault = UserVaultWrapper(self._app.vault, trans.user)
                for variable_payload in group.variables:
                    variable_name, variable_value = variable_payload.name, variable_payload.value
                    if variable_value is None:
                        continue
                    self._credentials_manager.add_variable(
                        session, variables, user_credential_group_id, variable_name, variable_value
                    )
                for secret_payload in group.secrets:
                    secret_name, secret_value = secret_payload.name, secret_payload.value
                    if secret_value is None:
                        continue
                    vault_ref = f"{source_type}|{source_id}|{reference}|{group_name}|{secret_name}"
                    user_vault.write_secret(vault_ref, secret_value)
                    self._credentials_manager.add_secret(
                        session, secrets, user_credential_group_id, secret_name, secret_value
                    )

            self._credentials_manager.update_current_group(trans, user_credentials_id, current_group_name)
        self._credentials_manager.commit_session(session)
