from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from sqlalchemy import select
from sqlalchemy.orm import aliased

from galaxy import exceptions
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import (
    Credential,
    CredentialsGroup,
    UserCredentials,
)
from galaxy.schema.credentials import (
    CredentialGroupResponse,
    CredentialsPayload,
    SecretResponse,
    SOURCE_TYPE,
    UpdateCredentialsPayload,
    UpdateGroupPayload,
    UserCredentialCreateResponse,
    UserCredentialsListResponse,
    UserCredentialsResponse,
    VariableResponse,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.security.vault import UserVaultWrapper
from galaxy.structured_app import StructuredApp
from galaxy.webapps.galaxy.api.common import UserIdPathParam


class CredentialsService:
    """Interface/service object shared by controllers for interacting with credentials."""

    def __init__(self, app: StructuredApp) -> None:
        self._app = app

    def list_user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> UserCredentialsListResponse:
        """Lists all credentials the user has provided (credentials themselves are not included)."""
        db_user_credentials = self._user_credentials(
            trans, user_id=user_id, source_type=source_type, source_id=source_id, group_name=group_name
        )
        credentials_dict = self._user_credentials_to_dict(db_user_credentials)
        return UserCredentialsListResponse(root=[UserCredentialsResponse(**cred) for cred in credentials_dict.values()])

    def provide_credential(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        payload: CredentialsPayload,
    ) -> UserCredentialCreateResponse:
        """Allows users to provide credentials for a group of secrets and variables."""
        return self._create_user_credential(trans, user_id, payload)

    def update_credential(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        user_credentials_id: DecodedDatabaseIdField,
        payload: UpdateCredentialsPayload,
    ):
        """Updates credentials for a group of secrets and variables."""
        return self._update_user_credential(trans, user_id, user_credentials_id, payload)

    def update_current_group_id(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        user_credentials_id: DecodedDatabaseIdField,
        payload: UpdateGroupPayload,
    ):
        """Updates the current group ID for a specific user credential."""
        self._update_current_group_id(trans, user_id, user_credentials_id, payload)

    def delete_service_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        user_credentials_id: DecodedDatabaseIdField,
    ):
        """Deletes all credentials for a specific service."""
        session = trans.sa_session

        user_credentials = self._user_credentials(trans, user_id=user_id, user_credentials_id=user_credentials_id)
        rows_to_be_deleted = {item for uc in user_credentials for item in uc}
        for row in rows_to_be_deleted:
            session.delete(row)
        session.commit()

    def delete_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        group_id: DecodedDatabaseIdField,
    ):
        """Deletes a specific credential group."""
        session = trans.sa_session

        user_credentials = self._user_credentials(trans, user_id=user_id, group_id=group_id)
        rows_to_be_deleted = {item for uc in user_credentials for item in uc if not isinstance(item, UserCredentials)}
        for row in rows_to_be_deleted:
            session.delete(row)
        session.commit()

    def _user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
        reference: Optional[str] = None,
        group_name: Optional[str] = None,
        user_credentials_id: Optional[DecodedDatabaseIdField] = None,
        group_id: Optional[DecodedDatabaseIdField] = None,
    ) -> List[Tuple[UserCredentials, CredentialsGroup, Credential]]:
        if not trans.user_is_admin and (not trans.user or trans.user != user_id):
            raise exceptions.ItemOwnershipException(
                "Only admins and the user can manage their own credentials.", type="error"
            )
        group_alias = aliased(CredentialsGroup)
        credential_alias = aliased(Credential)
        stmt = (
            select(UserCredentials, group_alias, credential_alias)
            .join(group_alias, group_alias.user_credentials_id == UserCredentials.id)
            .join(credential_alias, credential_alias.user_credential_group_id == group_alias.id)
            .where(UserCredentials.user_id == user_id)
        )
        if source_type:
            stmt = stmt.where(UserCredentials.source_type == source_type)
        if source_id:
            if not source_type:
                raise exceptions.RequestParameterInvalidException(
                    "Source type is required when source ID is provided.", type="error"
                )
            stmt = stmt.where(UserCredentials.source_id == source_id)
        if group_name:
            if not source_type or not source_id:
                raise exceptions.RequestParameterInvalidException(
                    "Source type and source ID are required when group name is provided.", type="error"
                )
            stmt = stmt.where(group_alias.name == group_name)

        if reference:
            stmt = stmt.where(UserCredentials.reference == reference)

        if user_credentials_id:
            stmt = stmt.where(UserCredentials.id == user_credentials_id)

        if group_id:
            stmt = stmt.where(group_alias.id == group_id)

        result = trans.sa_session.execute(stmt).all()
        return [(row[0], row[1], row[2]) for row in result]

    def _user_credentials_to_dict(
        self, db_user_credentials: List[Tuple[UserCredentials, CredentialsGroup, Credential]]
    ) -> Dict[int, Dict[str, Any]]:
        grouped_data: Dict[int, Dict[str, Any]] = {}
        group_name = {group.id: group.name for _, group, _ in db_user_credentials}
        for user_credentials, credentials_group, credential in db_user_credentials:
            grouped_data.setdefault(
                user_credentials.id,
                dict(
                    user_id=user_credentials.user_id,
                    id=user_credentials.id,
                    reference=user_credentials.reference,
                    source_type=user_credentials.source_type,
                    source_id=user_credentials.source_id,
                    current_group_id=user_credentials.current_group_id,
                    current_group_name=group_name[user_credentials.current_group_id],
                    groups={},
                ),
            )

            grouped_data[user_credentials.id]["groups"].setdefault(
                credentials_group.name,
                dict(
                    id=credentials_group.id,
                    name=credentials_group.name,
                    variables=[],
                    secrets=[],
                ),
            )

            if credential.type == "secret":
                grouped_data[user_credentials.id]["groups"][credentials_group.name]["secrets"].append(
                    dict(
                        id=credential.id,
                        name=credential.name,
                        already_set=True,
                    )
                )
            elif credential.type == "variable":
                grouped_data[user_credentials.id]["groups"][credentials_group.name]["variables"].append(
                    dict(
                        id=credential.id,
                        name=credential.name,
                        value=credential.value,
                    )
                )

        return grouped_data

    def _create_user_credential(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        payload: CredentialsPayload,
    ) -> UserCredentialCreateResponse:
        session = trans.sa_session

        source_type, source_id, reference, group_name = (
            payload.source_type,
            payload.source_id,
            payload.reference,
            payload.group_name,
        )

        db_user_credentials = self._user_credentials(
            trans,
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            reference=reference,
        )
        user_credential_dict = self._user_credentials_to_dict(db_user_credentials)
        if user_credential_dict:
            for user_credential_data in user_credential_dict.values():
                if group_name in user_credential_data["groups"]:
                    raise exceptions.RequestParameterInvalidException(
                        f"Group name '{group_name}' already exists for the given user credentials.", type="error"
                    )

        credentials_group = CredentialsGroup(name=group_name)
        session.add(credentials_group)
        session.flush()
        user_credential_group_id = credentials_group.id
        existing_user_credentials = next(iter(db_user_credentials), None)
        if existing_user_credentials:
            user_credentials = existing_user_credentials[0]
            user_credentials.current_group_id = user_credential_group_id
        else:
            user_credentials = UserCredentials(
                user_id=user_id,
                reference=reference,
                source_type=source_type,
                source_id=source_id,
                current_group_id=user_credential_group_id,
            )
            session.add(user_credentials)
            session.flush()

        user_credentials_id = user_credentials.id
        credentials_group.user_credentials_id = user_credentials_id
        session.add(credentials_group)

        user_vault = UserVaultWrapper(self._app.vault, trans.user)
        provided_credentials_list: List[Credential] = []
        for credential_payload in payload.credentials:
            credential_name, credential_type, credential_value = (
                credential_payload.name,
                credential_payload.type,
                credential_payload.value,
            )

            credential = Credential(
                user_credential_group_id=user_credential_group_id,
                name=credential_name,
                type=credential_type,
                value="",
            )

            if credential_type == "secret":
                vault_ref = f"{source_type}|{source_id}|{reference}|{group_name}|{credential_name}"
                user_vault.write_secret(vault_ref, credential_value or "")
                credential.value = "*" if credential_value else ""
            elif credential_type == "variable":
                credential.value = credential_value or ""
            provided_credentials_list.append(credential)
            session.add(credential)
        session.commit()

        variables = [
            VariableResponse(
                id=credential.id,
                name=credential.name,
                value=credential.value,
            )
            for credential in provided_credentials_list
            if credential.type == "variable"
        ]

        secrets = [
            SecretResponse(
                id=credential.id,
                name=credential.name,
                already_set=True if credential.value else False,
            )
            for credential in provided_credentials_list
            if credential.type == "secret"
        ]

        credentials_group_response = CredentialGroupResponse(
            id=user_credential_group_id,
            name=group_name,
            variables=variables,
            secrets=secrets,
        )

        return UserCredentialCreateResponse(
            user_id=user_id,
            id=user_credentials_id,
            source_type=source_type,
            source_id=source_id,
            reference=reference,
            current_group_name=group_name,
            group=credentials_group_response,
        )

    def _update_user_credential(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        user_credential_id: DecodedDatabaseIdField,
        payload: UpdateCredentialsPayload,
    ):
        db_user_credentials = self._user_credentials(trans, user_id=user_id, user_credentials_id=user_credential_id)

        existing_user_credentials = next(iter(db_user_credentials), None)
        if not existing_user_credentials:
            raise exceptions.ObjectNotFound("User credential not found.", type="error")

        user_vault = UserVaultWrapper(self._app.vault, trans.user)
        session = trans.sa_session
        for provided_credential in payload.credentials:
            user_credentials, user_credentials_group, existing_credential = None, None, None
            for cred in db_user_credentials:
                if cred[2].id == provided_credential.id:
                    user_credentials, user_credentials_group, existing_credential = cred
                    break
            if not existing_credential or not user_credentials or not user_credentials_group:
                raise exceptions.ObjectNotFound("Credential not found.", type="error")

            source_type, source_id, reference, group_name, credential_name = (
                user_credentials.source_type,
                user_credentials.source_id,
                user_credentials.reference,
                user_credentials_group.name,
                existing_credential.name,
            )

            if existing_credential and existing_credential.type == "secret":
                vault_ref = f"{source_type}|{source_id}|{reference}|{group_name}|{credential_name}"
                user_vault.write_secret(vault_ref, provided_credential.value or "")
                existing_credential.value = "*" if provided_credential.value else ""
            elif existing_credential and existing_credential.type == "variable":
                existing_credential.value = provided_credential.value or ""
            session.add(existing_credential)
        session.commit()

    def _update_current_group_id(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        user_credential_id: DecodedDatabaseIdField,
        payload: UpdateGroupPayload,
    ):
        db_user_credentials = self._user_credentials(trans, user_id=user_id, user_credentials_id=user_credential_id)

        existing_user_credentials = next(iter(db_user_credentials), None)
        if not existing_user_credentials:
            raise exceptions.ObjectNotFound("User credential not found.", type="error")
        user_credentials, _, _ = existing_user_credentials

        current_group_id = payload.current_group_id
        if not any(group.id == current_group_id for _, group, _ in db_user_credentials):
            raise exceptions.ObjectNotFound("Group ID not found in user credentials.", type="error")

        user_credentials.current_group_id = current_group_id

        session = trans.sa_session
        session.add(user_credentials)
        session.commit()
