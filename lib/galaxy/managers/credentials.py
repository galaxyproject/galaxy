from typing import (
    List,
    Optional,
    Tuple,
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

CredentialsModelsList = List[Union[UserCredentials, CredentialsGroup, Credential]]


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
    ) -> List[Tuple[UserCredentials, CredentialsGroup, Credential]]:
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

    def add_user_credentials(
        self,
        existing_user_credentials: List[Tuple[UserCredentials, CredentialsGroup, Credential]],
        user_id: DecodedDatabaseIdField,
        source_type: SOURCE_TYPE,
        source_id: str,
        source_version: str,
        name: str,
        version: str,
    ) -> DecodedDatabaseIdField:
        user_credentials = next(
            (
                uc
                for uc, *_ in existing_user_credentials
                if uc.user_id == user_id
                and uc.source_type == source_type
                and uc.source_id == source_id
                and uc.source_version == source_version
                and uc.name == name
                and uc.version == version
            ),
            None,
        )

        if not user_credentials:
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

    def add_group(
        self,
        existing_user_credentials: List[Tuple[UserCredentials, CredentialsGroup, Credential]],
        user_credentials_id: DecodedDatabaseIdField,
        group_name: str,
    ) -> DecodedDatabaseIdField:
        credentials_group = next(
            (
                creds_group
                for _, creds_group, _ in existing_user_credentials
                if creds_group.name == group_name and creds_group.user_credentials_id == user_credentials_id
            ),
            None,
        )

        if not credentials_group:
            credentials_group = CredentialsGroup(name=group_name, user_credentials_id=user_credentials_id)
            self.session.add(credentials_group)
            self.session.flush()

        return credentials_group.id

    def add_or_update_credential(
        self,
        existing_user_credentials: List[Tuple[UserCredentials, CredentialsGroup, Credential]],
        group_id: DecodedDatabaseIdField,
        name: str,
        value: Optional[str],
        is_secret: bool = False,
    ) -> None:
        credential = next(
            (
                cred
                for *_, cred in existing_user_credentials
                if cred and cred.name == name and cred.group_id == group_id and cred.is_secret == is_secret
            ),
            None,
        )
        if credential:
            if value is not None:
                credential.is_set = True
                if not is_secret:
                    credential.value = value
                self.session.add(credential)
        else:
            credential = Credential(
                group_id=group_id,
                name=name,
                is_secret=is_secret,
                is_set=bool(value),
                value=value if not is_secret else None,
            )
            self.session.add(credential)

    def update_current_group(
        self,
        user_id: DecodedDatabaseIdField,
        user_credentials_id: DecodedDatabaseIdField,
        group_name: Optional[str] = None,
    ) -> None:
        group_name = group_name or "default"
        existing_user_credentials = self.get_user_credentials(user_id, user_credentials_id=user_credentials_id)
        for user_credentials, credentials_group, _ in existing_user_credentials:
            if credentials_group.name == group_name:
                user_credentials.current_group_id = credentials_group.id
                self.session.add(user_credentials)
                break
        else:
            raise RequestParameterInvalidException("Group not found to set as current.")

    def delete_rows(
        self,
        rows_to_delete: CredentialsModelsList,
    ) -> None:
        for row in rows_to_delete:
            self.session.delete(row)
        self.session.commit()
