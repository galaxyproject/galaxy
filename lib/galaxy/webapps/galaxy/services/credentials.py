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
from galaxy.schema.credentials import (  # CredentialResponse,; UpdateCredentialsPayload,
    CredentialGroupResponse,
    CredentialsPayload,
    SecretResponse,
    SOURCE_TYPE,
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
        """Allows users to provide credentials for a secret/variable."""
        return self._create_user_credential(trans, user_id, payload)

    # def update_credential(
    #     self,
    #     trans: ProvidesUserContext,
    #     user_id: UserIdPathParam,
    #     user_credentials_id: DecodedDatabaseIdField,
    #     payload: UpdateCredentialsPayload,
    # ) -> CredentialsListResponse:
    #     """Updates credentials for a specific secret/variable."""
    #     return self._update_user_credential(trans, user_id, user_credentials_id, payload)

    # def delete_service_credentials(
    #     self,
    #     trans: ProvidesUserContext,
    #     user_id: UserIdPathParam,
    #     user_credentials_id: DecodedDatabaseIdField,
    # ):
    #     """Deletes all credentials for a specific service."""
    #     user_credentials = self._user_credentials(trans, user_id=user_id, user_credentials_id=user_credentials_id)
    #     session = trans.sa_session
    #     for credentials in credentials_dict.values():
    #         for credential in credentials:
    #             session.delete(credential)
    #     for user_credential in user_credentials:
    #         session.delete(user_credential)
    #         session.commit()

    # def delete_credentials(
    #     self,
    #     trans: ProvidesUserContext,
    #     user_id: UserIdPathParam,
    #     group_id: DecodedDatabaseIdField,
    #     credentials_id: DecodedDatabaseIdField,
    # ):
    #     """Deletes a specific credential group."""
    #     credentials = self._credentials(trans, group_id=group_id, id=credentials_id)
    #     session = trans.sa_session
    #     for credential in credentials:
    #         session.delete(credential)
    #     session.commit()

    def _user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
        reference: Optional[str] = None,
        group_name: Optional[str] = None,
        user_credentials_id: Optional[DecodedDatabaseIdField] = None,
    ) -> List[Tuple[UserCredentials, CredentialsGroup, Credential]]:
        if not trans.user_is_admin and (not trans.user or trans.user != user_id):
            raise exceptions.ItemOwnershipException(
                "Only admins and the user can manage their own credentials.", type="error"
            )
        group_alias = aliased(CredentialsGroup)
        credential_alias = aliased(Credential)
        stmt = (
            select(UserCredentials, group_alias, credential_alias)
            .join(group_alias, UserCredentials.groups)
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

        result = trans.sa_session.execute(stmt).all()
        return [(row[0], row[1], row[2]) for row in result]

    def _user_credentials_to_dict(
        self, db_user_credentials: List[Tuple[UserCredentials, CredentialsGroup, Credential]]
    ) -> Dict[int, Dict[str, Any]]:
        grouped_data: Dict[int, Dict[str, Any]] = {}
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
                    current_group_name=credentials_group.name,
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
        existing_user_credentials = next(iter(db_user_credentials), None)
        if existing_user_credentials:
            user_credentials = existing_user_credentials[0]
            user_credentials.current_group = credentials_group
        else:
            user_credentials = UserCredentials(
                user_id=user_id,
                reference=reference,
                source_type=source_type,
                source_id=source_id,
                current_group=credentials_group,
            )
        credentials_group.user_credentials_rel = user_credentials
        session.add(user_credentials)
        session.flush()
        user_credentials_id = user_credentials.id
        user_credential_group_id = credentials_group.id

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
                user_vault = UserVaultWrapper(self._app.vault, trans.user)
                user_vault.write_secret(
                    f"{source_type}|{source_id}|{reference}|{group_name}|{credential_name}", credential_value
                )
            elif credential_type == "variable":
                credential.value = credential_value
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
                already_set=True,
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

    # def _update_user_credential(
    #     self,
    #     trans: ProvidesUserContext,
    #     user_id: UserIdPathParam,
    #     user_credential_id: DecodedDatabaseIdField,
    #     payload: UpdateCredentialsPayload,
    # ) -> CredentialsListResponse:
    #     user_credential = next(self._user_credentials(trans, user_id, user_credentials_id=user_credential_id), None)
    #     if not user_credential:
    #         raise exceptions.ObjectNotFound(f"User credential {user_credential_id} not found.", type="error")
    #     db_credentials = user_credential.credentials
    #     session = trans.sa_session
    #     group_id = payload.group_id
    #     for credential in payload.credentials:
    #         existing_credential = next(
    #             (cred for cred in db_credentials if cred.id == credential.id),
    #             None,
    #         )
    #         if not existing_credential:
    #             raise exceptions.ObjectNotFound(f"Credential {credential.id} not found.", type="error")

    #         if existing_credential.type == "secret":
    #             user_vault = UserVaultWrapper(self._app.vault, trans.user)
    #             user_vault.write_secret(f"{user_credential.reference}|{existing_credential.name}", credential.value)
    #         elif existing_credential.type == "variable":
    #             existing_credential.value = credential.value
    #         session.add(existing_credential)
    #         session.commit()
    #     return CredentialsListResponse(
    #         user_credentials_id=user_credential_id,
    #         source_type=user_credential.source_type,
    #         source_id=user_credential.source_id,
    #         reference=user_credential.reference,
    #         group_name=user_credential.group_name,
    #         credentials=self._credentials_response(db_credentials),
    #     )
