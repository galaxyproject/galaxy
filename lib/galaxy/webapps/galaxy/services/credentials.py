from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
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
from galaxy.schema.schema import FlexibleUserIdType
from galaxy.security.vault import UserVaultWrapper
from galaxy.structured_app import StructuredApp


class CredentialsService:
    """Interface/service object shared by controllers for interacting with credentials."""

    def __init__(self, app: StructuredApp) -> None:
        self._app = app

    def list_user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> UserCredentialsListResponse:
        """Lists all credentials the user has provided (credentials themselves are not included)."""
        db_user_credentials = self._user_credentials(
            trans, user_id=user_id, source_type=source_type, source_id=source_id, group_name=group_name
        )
        credentials_dict = self._user_credentials_to_dict(db_user_credentials)
        for user_credentials, credentials_group in db_user_credentials:
            variables, secrets = self._credentials(trans, group_id=credentials_group.id)
            group = credentials_dict.get(user_credentials.id, {}).get("groups", {}).get(credentials_group.name, {})
            self._add_credential_to_group(group, variables, secrets)

        return UserCredentialsListResponse(root=[UserCredentialsResponse(**cred) for cred in credentials_dict.values()])

    def provide_credential(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        payload: CreateSourceCredentialsPayload,
    ) -> UserCredentialsListResponse:
        """Allows users to provide credentials for a group of secrets and variables."""
        return self._create_user_credential(trans, user_id, payload)

    def delete_service_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        user_credentials_id: DecodedDatabaseIdField,
    ):
        """Deletes all credentials for a specific service."""
        db_user_credentials = self._user_credentials(trans, user_id=user_id, user_credentials_id=user_credentials_id)
        rows_to_be_deleted: List[Union[UserCredentials, CredentialsGroup, Variable, Secret]] = []
        for uc, credentials_group in db_user_credentials:
            variables, secrets = self._credentials(trans, group_id=credentials_group.id)
            rows_to_be_deleted.extend([uc, credentials_group, *variables, *secrets])
        self._delete_credentials(trans.sa_session, rows_to_be_deleted)

    def delete_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        group_id: DecodedDatabaseIdField,
    ):
        """Deletes a specific credential group."""
        user_credentials = self._user_credentials(trans, user_id=user_id, group_id=group_id)
        rows_to_be_deleted: List[Union[CredentialsGroup, Variable, Secret]] = []
        for _, credentials_group in user_credentials:
            variables, secrets = self._credentials(trans, group_id=credentials_group.id)
            rows_to_be_deleted.extend([credentials_group, *variables, *secrets])
        self._delete_credentials(trans.sa_session, rows_to_be_deleted)

    def _user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
        reference: Optional[str] = None,
        group_name: Optional[str] = None,
        user_credentials_id: Optional[DecodedDatabaseIdField] = None,
        group_id: Optional[DecodedDatabaseIdField] = None,
    ) -> List[Tuple[UserCredentials, CredentialsGroup]]:
        if trans.anonymous:
            raise exceptions.AuthenticationRequired("You need to be logged in to access your credentials.")
        if user_id == "current":
            user_id = trans.user.id
        if trans.user and trans.user.id != user_id:
            raise exceptions.ItemOwnershipException("You can only access your own credentials.")
        user_cred_alias = aliased(UserCredentials)
        group_alias = aliased(CredentialsGroup)
        stmt = (
            select(user_cred_alias, group_alias)
            .join(group_alias, group_alias.user_credentials_id == user_cred_alias.id)
            .where(user_cred_alias.user_id == user_id)
        )
        if source_type:
            stmt = stmt.where(user_cred_alias.source_type == source_type)
        if source_id:
            if not source_type:
                raise exceptions.RequestParameterInvalidException(
                    "Source type is required when source ID is provided.", type="error"
                )
            stmt = stmt.where(user_cred_alias.source_id == source_id)
        if group_name:
            if not source_type or not source_id:
                raise exceptions.RequestParameterInvalidException(
                    "Source type and source ID are required when group name is provided.", type="error"
                )
            stmt = stmt.where(group_alias.name == group_name)

        if reference:
            stmt = stmt.where(user_cred_alias.reference == reference)

        if user_credentials_id:
            stmt = stmt.where(user_cred_alias.id == user_credentials_id)

        if group_id:
            stmt = stmt.where(group_alias.id == group_id)

        result = trans.sa_session.execute(stmt).all()
        return [(row[0], row[1]) for row in result]

    def _credentials(
        self,
        trans: ProvidesUserContext,
        group_id: DecodedDatabaseIdField,
    ) -> Tuple[List[Variable], List[Secret]]:
        variables_stmt = select(Variable).where(Variable.user_credential_group_id == group_id)
        secrets_stmt = select(Secret).where(Secret.user_credential_group_id == group_id)

        variables_result = list(trans.sa_session.execute(variables_stmt).scalars().all())
        secrets_result = list(trans.sa_session.execute(secrets_stmt).scalars().all())

        return variables_result, secrets_result

    def _user_credentials_to_dict(
        self,
        db_user_credentials: List[Tuple[UserCredentials, CredentialsGroup]],
    ) -> Dict[int, Dict[str, Any]]:
        grouped_data: Dict[int, Dict[str, Any]] = {}
        group_name = {group.id: group.name for _, group in db_user_credentials}
        for user_credentials, credentials_group in db_user_credentials:
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

        return grouped_data

    def _add_credential_to_group(
        self,
        group: Dict[str, Any],
        variables: List[Variable],
        secrets: List[Secret],
    ) -> None:
        for variable in variables:
            group["variables"].append({"id": variable.id, "name": variable.name, "value": variable.value})
        for secret in secrets:
            group["secrets"].append({"id": secret.id, "name": secret.name, "already_set": secret.already_set})

    def _create_user_credential(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
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
        credentials_dict = self._user_credentials_to_dict(db_user_credentials)
        existing_groups = {
            cred["reference"]: {group["name"]: group["id"] for group in cred["groups"].values()}
            for cred in credentials_dict.values()
        }

        for service_payload in payload.credentials:
            reference = service_payload.reference
            current_group_name = service_payload.current_group
            current_group_id = existing_groups.get(reference, {}).get(current_group_name)

            user_credentials = next((uc[0] for uc in db_user_credentials if uc[0].reference == reference), None)
            if not user_credentials:
                if user_id == "current":
                    user_id = trans.user.id
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
                    (uc[1] for uc in db_user_credentials if uc[1].name == group_name and uc[0].reference == reference),
                    None,
                )
                if not credentials_group:
                    credentials_group = CredentialsGroup(name=group_name, user_credentials_id=user_credentials_id)
                    session.add(credentials_group)
                    session.flush()
                user_credential_group_id = credentials_group.id

                if current_group_name == group_name:
                    current_group_id = user_credential_group_id

                variables, secrets = self._credentials(trans, group_id=user_credential_group_id)
                user_vault = UserVaultWrapper(self._app.vault, trans.user)
                for variable_payload in group.variables:
                    variable_name, variable_value = variable_payload.name, variable_payload.value
                    variable = next(
                        (var for var in variables if var.name == variable_name),
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
                        (sec for sec in secrets if sec.name == secret_name),
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

        new_user_credentials = db_user_credentials or self._user_credentials(
            trans,
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
        )
        credentials_dict = self._user_credentials_to_dict(new_user_credentials)
        for new_user_credentials_list, new_credentials_group in new_user_credentials:
            variables, secrets = self._credentials(trans, group_id=new_credentials_group.id)
            db_group = (
                credentials_dict.get(new_user_credentials_list.id, {})
                .get("groups", {})
                .get(new_credentials_group.name, {})
            )
            self._add_credential_to_group(db_group, variables, secrets)
        return UserCredentialsListResponse(root=[UserCredentialsResponse(**cred) for cred in credentials_dict.values()])

    def _delete_credentials(self, sa_session: galaxy_scoped_session, rows_to_be_deleted: List):
        for row in rows_to_be_deleted:
            sa_session.delete(row)
        sa_session.commit()
