from typing import (
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
from galaxy.schema.credentials import SOURCE_TYPE
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import FlexibleUserIdType


class CredentialsManager:
    """Manager object shared by controllers for interacting with credentials."""

    def get_user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
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

    def add_user_credentials(
        self,
        session: galaxy_scoped_session,
        db_user_credentials: List[Tuple[UserCredentials, CredentialsGroup]],
        user_id: DecodedDatabaseIdField,
        reference: str,
        source_type: SOURCE_TYPE,
        source_id: str,
    ) -> DecodedDatabaseIdField:
        user_credentials = next((uc[0] for uc in db_user_credentials if uc[0].reference == reference), None)
        if not user_credentials:
            user_credentials = UserCredentials(
                user_id=user_id,
                reference=reference,
                source_type=source_type,
                source_id=source_id,
            )
            session.add(user_credentials)
            session.flush()
        return user_credentials.id

    def add_group(
        self,
        session: galaxy_scoped_session,
        db_user_credentials: List[Tuple[UserCredentials, CredentialsGroup]],
        user_credentials_id: DecodedDatabaseIdField,
        group_name: str,
        reference: str,
    ) -> DecodedDatabaseIdField:
        credentials_group = next(
            (uc[1] for uc in db_user_credentials if uc[1].name == group_name and uc[0].reference == reference),
            None,
        )
        if not credentials_group:
            credentials_group = CredentialsGroup(name=group_name, user_credentials_id=user_credentials_id)
            session.add(credentials_group)
            session.flush()
        return credentials_group.id

    def add_variable(
        self,
        session: galaxy_scoped_session,
        variables: List[Variable],
        user_credential_group_id: DecodedDatabaseIdField,
        variable_name: str,
        variable_value: str,
    ) -> None:
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

    def add_secret(
        self,
        session: galaxy_scoped_session,
        secrets: List[Secret],
        user_credential_group_id: DecodedDatabaseIdField,
        secret_name: str,
        secret_value: str,
    ) -> None:
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

    def commit_session(
        self,
        session: galaxy_scoped_session,
    ) -> None:
        with transaction(session):
            session.commit()

    def update_current_group(
        self,
        trans: ProvidesUserContext,
        user_credentials_id: DecodedDatabaseIdField,
        group_name: str,
    ) -> None:
        db_user_credentials = self.get_user_credentials(trans, trans.user.id, user_credentials_id=user_credentials_id)
        for user_credentials, credentials_group in db_user_credentials:
            if credentials_group.name == group_name:
                user_credentials.current_group_id = credentials_group.id
                trans.sa_session.add(user_credentials)
                break
        else:
            raise RequestParameterInvalidException("Group not found to set as current.")

    def delete_rows(
        self,
        session: galaxy_scoped_session,
        rows_to_delete: List,
    ) -> None:
        for row in rows_to_delete:
            session.delete(row)
        with transaction(session):
            session.commit()
