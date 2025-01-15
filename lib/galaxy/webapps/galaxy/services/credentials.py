from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from galaxy.exceptions import ObjectNotFound
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


class CredentialsService:
    """Service object shared by controllers for interacting with credentials."""

    def __init__(
        self,
        credentials_manager: CredentialsManager,
    ) -> None:
        self._credentials_manager = credentials_manager

    def list_user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> UserCredentialsListResponse:
        """Lists all credentials the user has provided (credentials themselves are not included)."""
        return self._list_user_credentials(trans, user_id, source_type, source_id, group_name)

    def provide_credential(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        payload: CreateSourceCredentialsPayload,
    ) -> UserCredentialsListResponse:
        """Allows users to provide credentials for a group of secrets and variables."""
        source_type, source_id = payload.source_type, payload.source_id
        db_user_credentials = self._credentials_manager.get_user_credentials(trans, user_id, source_type, source_id)
        credentials_dict = self._map_user_credentials(db_user_credentials)
        self._credentials_manager.create_or_update_credentials(trans, payload, db_user_credentials, credentials_dict)
        return self._list_user_credentials(trans, user_id, source_type, source_id)

    def delete_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        group_id: Optional[DecodedDatabaseIdField] = None,
        user_credentials_id: Optional[DecodedDatabaseIdField] = None,
    ) -> None:
        """Deletes a specific credential group or all credentials for a specific service."""
        db_user_credentials = self._credentials_manager.get_user_credentials(
            trans, user_id, group_id=group_id, user_credentials_id=user_credentials_id
        )
        if not db_user_credentials:
            raise ObjectNotFound("No credentials found.")
        rows_to_delete: List[Union[UserCredentials, CredentialsGroup, Variable, Secret]] = []
        for uc, credentials_group in db_user_credentials:
            if not group_id:
                rows_to_delete.append(uc)
            variables, secrets = self._credentials_manager.fetch_credentials(trans.sa_session, credentials_group.id)
            rows_to_delete.extend([credentials_group, *variables, *secrets])
        self._credentials_manager.delete_rows(trans.sa_session, rows_to_delete)

    def _list_user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> UserCredentialsListResponse:
        db_user_credentials = self._credentials_manager.get_user_credentials(
            trans, user_id, source_type, source_id, group_name
        )
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
