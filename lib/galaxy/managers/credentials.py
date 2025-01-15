from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from sqlalchemy import select
from sqlalchemy.orm import aliased

from galaxy.exceptions import (
    AuthenticationRequired,
    ItemOwnershipException,
    RequestParameterInvalidException,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import (
    CredentialsGroup,
    Secret,
    UserCredentials,
    Variable,
)
from galaxy.model.base import transaction
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.credentials import (
    CreateSourceCredentialsPayload,
    SOURCE_TYPE,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import FlexibleUserIdType
from galaxy.security.vault import UserVaultWrapper
from galaxy.structured_app import StructuredApp


class CredentialsManager:
    """Manager object shared by controllers for interacting with credentials."""

    def __init__(self, app: StructuredApp) -> None:
        self._app = app

    def get_user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
        group_name: Optional[str] = None,
        user_credentials_id: Optional[DecodedDatabaseIdField] = None,
        group_id: Optional[DecodedDatabaseIdField] = None,
    ) -> List[Tuple[UserCredentials, CredentialsGroup]]:
        if trans.anonymous:
            raise AuthenticationRequired("You need to be logged in to access your credentials.")
        if user_id == "current":
            user_id = trans.user.id
        elif trans.user.id != user_id:
            raise ItemOwnershipException("You can only access your own credentials.")
        user_cred_alias, group_alias = aliased(UserCredentials), aliased(CredentialsGroup)
        stmt = (
            select(user_cred_alias, group_alias)
            .join(group_alias, group_alias.user_credentials_id == user_cred_alias.id)
            .where(user_cred_alias.user_id == user_id)
        )
        if source_type:
            stmt = stmt.where(user_cred_alias.source_type == source_type)
        if source_id:
            if not source_type:
                raise RequestParameterInvalidException("Source type is required when source ID is provided.")
            stmt = stmt.where(user_cred_alias.source_id == source_id)
        if group_name:
            stmt = stmt.where(group_alias.name == group_name)
        if user_credentials_id:
            stmt = stmt.where(user_cred_alias.id == user_credentials_id)
        if group_id:
            stmt = stmt.where(group_alias.id == group_id)

        result = trans.sa_session.execute(stmt).all()
        return [(row[0], row[1]) for row in result]

    def fetch_credentials(
        self,
        session: galaxy_scoped_session,
        group_id: DecodedDatabaseIdField,
    ) -> Tuple[List[Variable], List[Secret]]:
        variables = list(
            session.execute(select(Variable).where(Variable.user_credential_group_id == group_id)).scalars().all()
        )

        secrets = list(
            session.execute(select(Secret).where(Secret.user_credential_group_id == group_id)).scalars().all()
        )

        return variables, secrets

    def create_or_update_credentials(
        self,
        trans: ProvidesUserContext,
        payload: CreateSourceCredentialsPayload,
        db_user_credentials: List[Tuple[UserCredentials, CredentialsGroup]],
        credentials_dict: Dict[int, Dict[str, Any]],
    ) -> None:
        session = trans.sa_session
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
                user_credentials = UserCredentials(
                    user_id=trans.user.id,
                    reference=reference,
                    source_type=payload.source_type,
                    source_id=payload.source_id,
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
                variables, secrets = self.fetch_credentials(trans.sa_session, user_credential_group_id)
                user_vault = UserVaultWrapper(self._app.vault, trans.user)
                for variable_payload in group.variables:
                    variable_name, variable_value = variable_payload.name, variable_payload.value
                    if variable_value is None:
                        continue
                    variable = next(
                        (var for var in variables if var.name == variable_name),
                        None,
                    )
                    if variable:
                        variable.value = variable_value
                    else:
                        variable = Variable(
                            user_credential_group_id=user_credential_group_id,
                            name=variable_name,
                            value=variable_value,
                        )
                    session.add(variable)
                for secret_payload in group.secrets:
                    secret_name, secret_value = secret_payload.name, secret_payload.value
                    if secret_value is None:
                        continue
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
                    vault_ref = f"{payload.source_type}|{payload.source_id}|{reference}|{group_name}|{secret_name}"
                    user_vault.write_secret(vault_ref, secret_value)
            if not current_group_id:
                raise RequestParameterInvalidException("No current group selected.")
            user_credentials.current_group_id = current_group_id
            session.add(user_credentials)

        with transaction(session):
            session.commit()

    def delete_rows(
        self,
        session: galaxy_scoped_session,
        rows_to_delete: List,
    ) -> None:
        for row in rows_to_delete:
            session.delete(row)
        with transaction(session):
            session.commit()
