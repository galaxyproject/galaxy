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
        credentials_dict = self._user_credentials_to_dict(db_user_credentials).values()
        return UserCredentialsListResponse(root=[UserCredentialsResponse(**cred) for cred in credentials_dict])

    def provide_credential(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        payload: CreateSourceCredentialsPayload,
    ) -> UserCredentialsListResponse:
        """Allows users to provide credentials for a group of secrets and variables."""
        return self._create_user_credential(trans, user_id, payload)

    def delete_service_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        user_credentials_id: DecodedDatabaseIdField,
    ):
        """Deletes all credentials for a specific service."""
        user_credentials = self._user_credentials(trans, user_id=user_id, user_credentials_id=user_credentials_id)
        rows_to_be_deleted = {item for uc in user_credentials for item in uc}
        self._delete_credentials(trans.sa_session, rows_to_be_deleted)

    def delete_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        group_id: DecodedDatabaseIdField,
    ):
        """Deletes a specific credential group."""
        user_credentials = self._user_credentials(trans, user_id=user_id, group_id=group_id)
        rows_to_be_deleted = {item for uc in user_credentials for item in uc if not isinstance(item, UserCredentials)}
        self._delete_credentials(trans.sa_session, rows_to_be_deleted)

    def _user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,  # TODO: use FlexibleUserIdType to support also "current"
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
        reference: Optional[str] = None,
        group_name: Optional[str] = None,
        user_credentials_id: Optional[DecodedDatabaseIdField] = None,
        group_id: Optional[DecodedDatabaseIdField] = None,
    ) -> List[Tuple[UserCredentials, CredentialsGroup, Variable, Secret]]:
        if trans.anonymous:
            raise exceptions.AuthenticationRequired("You need to be logged in to access your credentials.")
        if trans.user and trans.user.id != user_id:
            raise exceptions.ItemOwnershipException("You can only access your own credentials.")
        group_alias = aliased(CredentialsGroup)
        var_alias = aliased(Variable)
        sec_alias = aliased(Secret)
        stmt = (
            select(UserCredentials, group_alias, var_alias, sec_alias)
            .join(group_alias, group_alias.user_credentials_id == UserCredentials.id)
            .outerjoin(var_alias, var_alias.user_credential_group_id == group_alias.id)
            .outerjoin(sec_alias, sec_alias.user_credential_group_id == group_alias.id)
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
        return [(row[0], row[1], row[2], row[3]) for row in result]

    def _user_credentials_to_dict(
        self,
        db_user_credentials: List[Tuple[UserCredentials, CredentialsGroup, Variable, Secret]],
    ) -> Dict[int, Dict[str, Any]]:
        grouped_data: Dict[int, Dict[str, Any]] = {}
        group_name = {group.id: group.name for _, group, _, _ in db_user_credentials}
        for user_credentials, credentials_group, variable, secret in db_user_credentials:
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

            group = grouped_data[user_credentials.id]["groups"][credentials_group.name]
            group["secrets"].append({"id": secret.id, "name": secret.name, "already_set": True})
            group["variables"].append({"id": variable.id, "name": variable.name, "value": variable.value})

        return grouped_data

    def _create_user_credential(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        payload: CreateSourceCredentialsPayload,
    ) -> UserCredentialsListResponse:
        session = trans.sa_session

        source_type, source_id = payload.source_type, payload.source_id

        db_user_credentials = self._user_credentials(
            trans,
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
        )
        credentials_dict = self._user_credentials_to_dict(db_user_credentials).values()
        existing_groups = {
            cred["reference"]: {group["name"]: group["id"] for group in cred["groups"].values()}
            for cred in credentials_dict
        }

        for service_payload in payload.credentials:
            reference = service_payload.reference
            current_group_name = service_payload.current_group
            current_group_id = existing_groups.get(reference, {}).get(current_group_name)

            user_credentials = next((cred[0] for cred in db_user_credentials if cred[0].reference == reference), None)
            if not user_credentials:
                user_credentials = UserCredentials(
                    user_id=user_id,
                    reference=reference,
                    source_type=source_type,
                    source_id=source_id,
                )
                session.add(user_credentials)
                session.flush()
            user_credentials_id = user_credentials.id

            for group in service_payload.groups:
                group_name = group.name

                credentials_group = next(
                    (group[1] for group in db_user_credentials if group[1].name == group_name), None
                )
                if not credentials_group:
                    credentials_group = CredentialsGroup(name=group_name, user_credentials_id=user_credentials_id)
                    session.add(credentials_group)
                    session.flush()
                user_credential_group_id = credentials_group.id

                if current_group_name == group_name:
                    current_group_id = user_credential_group_id

                user_vault = UserVaultWrapper(self._app.vault, trans.user)
                for variable_payload in group.variables:
                    variable_name, variable_value = variable_payload.name, variable_payload.value
                    variable = next(
                        (
                            var[2]
                            for var in db_user_credentials
                            if var[1].name == group_name and var[2].name == variable_name
                        ),
                        None,
                    )
                    if variable:
                        variable.value = variable_value or ""
                    else:
                        variable = Variable(
                            user_credential_group_id=user_credential_group_id,
                            name=variable_name,
                            value=variable_value or "",
                        )
                    session.add(variable)
                for secret_payload in group.secrets:
                    secret_name, secret_value = secret_payload.name, secret_payload.value

                    secret = next(
                        (
                            sec[3]
                            for sec in db_user_credentials
                            if sec[1].name == group_name and sec[3].name == secret_name
                        ),
                        None,
                    )
                    if secret:
                        secret.already_set = True if secret_value else False
                    else:
                        secret = Secret(
                            user_credential_group_id=user_credential_group_id,
                            name=secret_name,
                            already_set=True if secret_value else False,
                        )
                    session.add(secret)
                    vault_ref = f"{source_type}|{source_id}|{reference}|{group_name}|{secret_name}"
                    user_vault.write_secret(vault_ref, secret_value or "")
            if not current_group_id:
                raise exceptions.RequestParameterInvalidException(
                    "No group was selected as the current group.", type="error"
                )
            user_credentials.current_group_id = current_group_id
            session.add(user_credentials)
        session.commit()

        credentials_dict = self._user_credentials_to_dict(db_user_credentials).values()
        return UserCredentialsListResponse(root=[UserCredentialsResponse(**cred) for cred in credentials_dict])

    def _delete_credentials(self, sa_session: galaxy_scoped_session, rows_to_be_deleted: set):
        for row in rows_to_be_deleted:
            sa_session.delete(row)
        sa_session.commit()
