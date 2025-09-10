from typing import (
    Optional,
    Union,
)

from sqlalchemy import select
from sqlalchemy.orm import aliased

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model import (
    Credential,
    CredentialsGroup,
    UserCredentials,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.credentials import SOURCE_TYPE
from galaxy.schema.fields import DecodedDatabaseIdField

CredentialsModelsSet = set[Union[UserCredentials, CredentialsGroup, Credential]]
CredentialsAssociation = list[tuple[UserCredentials, CredentialsGroup, Credential]]


def build_vault_credential_reference(
    source_type: str, source_id: str, service_name: str, service_version: str, group_id: int, secret_name: str
) -> str:
    """Builds a unique reference string for a credential stored in the vault."""
    vault_ref = f"{source_type}|{source_id}|{service_name}|{service_version}|{group_id}|{secret_name}"
    return vault_ref


class CredentialsManager:
    """Manager object shared by controllers for interacting with credentials."""

    def __init__(self, session: galaxy_scoped_session) -> None:
        self.session = session

    def get_user_credentials(
        self,
        user_id: DecodedDatabaseIdField,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
        source_version: Optional[str] = None,
        user_credentials_id: Optional[DecodedDatabaseIdField] = None,
        group_id: Optional[DecodedDatabaseIdField] = None,
    ) -> CredentialsAssociation:
        if source_id and not source_type:
            raise RequestParameterInvalidException("Source type is required when source ID is provided.")

        user_cred_alias, group_alias, cred_alias = (
            aliased(UserCredentials),
            aliased(CredentialsGroup),
            aliased(Credential),
        )
        stmt = (
            select(user_cred_alias, group_alias, cred_alias)
            .join(group_alias, group_alias.user_credentials_id == user_cred_alias.id)
            .outerjoin(cred_alias, cred_alias.group_id == group_alias.id)
            .where(user_cred_alias.user_id == user_id)
        )
        if source_type:
            stmt = stmt.where(user_cred_alias.source_type == source_type)
        if source_id:
            stmt = stmt.where(user_cred_alias.source_id == source_id)
        if source_version:
            stmt = stmt.where(user_cred_alias.source_version == source_version)
        if user_credentials_id:
            stmt = stmt.where(user_cred_alias.id == user_credentials_id)
        if group_id:
            stmt = stmt.where(group_alias.id == group_id)

        result = self.session.execute(stmt).tuples().all()
        return list(result)

    def index_credentials(self, existing_user_credentials: CredentialsAssociation) -> tuple[
        dict[tuple[str, str], UserCredentials],
        dict[tuple[DecodedDatabaseIdField, str], CredentialsGroup],
        dict[tuple[DecodedDatabaseIdField, str, bool], Credential],
    ]:
        user_cred_map = {}
        group_map = {}
        cred_map = {}

        for uc, group, cred in existing_user_credentials:
            if uc:
                user_cred_map[(uc.name, uc.version)] = uc
            if group:
                group_map[(group.user_credentials_id, group.name)] = group
            if cred:
                cred_map[(cred.group_id, cred.name, cred.is_secret)] = cred

        return user_cred_map, group_map, cred_map

    def add_user_credentials(
        self,
        user_id: DecodedDatabaseIdField,
        source_type: SOURCE_TYPE,
        source_id: str,
        source_version: str,
        name: str,
        version: str,
    ) -> DecodedDatabaseIdField:
        user_credentials = UserCredentials(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            source_version=source_version,
            name=name,
            version=version,
        )
        self.session.add(user_credentials)
        self.session.flush()
        return user_credentials.id

    def update_group(
        self,
        credentials_group: CredentialsGroup,
        group_name: str,
    ) -> None:
        credentials_group.name = group_name
        self.session.add(credentials_group)

    def add_group(
        self,
        user_credentials_id: DecodedDatabaseIdField,
        group_name: str,
    ) -> DecodedDatabaseIdField:
        credentials_group = CredentialsGroup(name=group_name, user_credentials_id=user_credentials_id)
        self.session.add(credentials_group)
        self.session.flush()
        return credentials_group.id

    def update_credential(
        self,
        credential: Credential,
        value: Optional[str] = None,
        is_secret: bool = False,
    ) -> None:
        credential.is_set = bool(value)
        credential.value = value if not is_secret else None
        self.session.add(credential)

    def add_credential(
        self,
        group_id: DecodedDatabaseIdField,
        name: str,
        value: Optional[str] = None,
        is_secret: bool = False,
    ) -> None:
        credential = Credential(
            group_id=group_id,
            name=name,
            is_secret=is_secret,
            is_set=bool(value),
            value=value if not is_secret else None,
        )
        self.session.add(credential)
        self.session.flush()

    def update_current_group(
        self,
        user_credentials: UserCredentials,
        group_id: Optional[DecodedDatabaseIdField] = None,
    ) -> None:
        user_credentials.current_group_id = group_id
        self.session.add(user_credentials)

    def delete_rows(
        self,
        rows_to_delete: CredentialsModelsSet,
    ) -> None:
        for row in rows_to_delete:
            self.session.delete(row)
        self.session.commit()
