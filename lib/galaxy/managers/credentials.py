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
        service_reference: str,
        source_type: SOURCE_TYPE,
        source_id: str,
    ) -> DecodedDatabaseIdField:
        user_credentials = next(
            (uc[0] for uc in existing_user_credentials if uc[0].service_reference == service_reference), None
        )
        if not user_credentials:
            user_credentials = UserCredentials(
                user_id=user_id,
                service_reference=service_reference,
                source_type=source_type,
                source_id=source_id,
            )
            self.session.add(user_credentials)
            self.session.flush()
        return user_credentials.id

    def add_group(
        self,
        existing_user_credentials: List[Tuple[UserCredentials, CredentialsGroup, Credential]],
        user_credentials_id: DecodedDatabaseIdField,
        group_name: str,
        service_reference: str,
    ) -> DecodedDatabaseIdField:
        credentials_group = next(
            (
                uc[1]
                for uc in existing_user_credentials
                if uc[1].name == group_name and uc[0].service_reference == service_reference
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
        value: str,
        is_secret: bool = False,
    ) -> None:
        credential = next(
            (
                uc[2]
                for uc in existing_user_credentials
                if uc[2] and uc[2].name == name and uc[2].group_id == group_id and uc[2].is_secret == is_secret
            ),
            None,
        )
        if credential:
            credential.is_set = bool(value)
            if not is_secret:
                credential.value = value
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
        group_name: str,
    ) -> None:
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
