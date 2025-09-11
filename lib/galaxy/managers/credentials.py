from typing import (
    Optional,
    Union,
)

from sqlalchemy import select
from sqlalchemy.orm import scoped_session

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model import (
    Credential,
    CredentialsGroup,
    User,
    UserCredentials,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.credentials import SOURCE_TYPE
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.security.vault import (
    UserVaultWrapper,
    Vault,
)
from galaxy.tool_util.deps.requirements import CredentialsRequirement

CredentialsModelsSet = set[Union[UserCredentials, CredentialsGroup, Credential]]
CredentialsAssociation = list[tuple[UserCredentials, CredentialsGroup, Credential]]


def _build_user_credentials_query(
    user_id: DecodedDatabaseIdField,
    source_type: Optional[str] = None,
    source_id: Optional[str] = None,
    source_version: Optional[str] = None,
    service_name: Optional[str] = None,
    service_version: Optional[str] = None,
    user_credentials_id: Optional[DecodedDatabaseIdField] = None,
    group_id: Optional[DecodedDatabaseIdField] = None,
    current_group_only: bool = False,
):
    """
    Builds a common SQLAlchemy query for fetching user credentials with optional filters.

    Args:
        user_id: ID of the user
        source_type: Filter by source type
        source_id: Filter by source ID
        source_version: Filter by source version
        service_name: Filter by service name (maps to UserCredentials.name)
        service_version: Filter by service version (maps to UserCredentials.version)
        user_credentials_id: Filter by specific user credentials ID
        group_id: Filter by specific group ID
        current_group_only: If True, only return credentials from the current active group

    Returns:
        SQLAlchemy query object that can be executed
    """
    if source_id and not source_type:
        raise RequestParameterInvalidException("Source type is required when source ID is provided.")

    stmt = (
        select(UserCredentials, CredentialsGroup, Credential)
        .join(CredentialsGroup, CredentialsGroup.user_credentials_id == UserCredentials.id)
        .outerjoin(Credential, Credential.group_id == CredentialsGroup.id)
        .where(UserCredentials.user_id == user_id)
    )

    if current_group_only:
        stmt = stmt.where(UserCredentials.current_group_id == CredentialsGroup.id)

    if source_type:
        stmt = stmt.where(UserCredentials.source_type == source_type)
    if source_id:
        stmt = stmt.where(UserCredentials.source_id == source_id)
    if source_version:
        stmt = stmt.where(UserCredentials.source_version == source_version)
    if service_name:
        stmt = stmt.where(UserCredentials.name == service_name)
    if service_version:
        stmt = stmt.where(UserCredentials.version == service_version)
    if user_credentials_id:
        stmt = stmt.where(UserCredentials.id == user_credentials_id)
    if group_id:
        stmt = stmt.where(CredentialsGroup.id == group_id)

    return stmt


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
        stmt = _build_user_credentials_query(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            source_version=source_version,
            user_credentials_id=user_credentials_id,
            group_id=group_id,
        )
        result = self.session.execute(stmt).tuples().all()
        return list(result)

    def index_credentials(self, existing_user_credentials: CredentialsAssociation) -> tuple[
        dict[tuple[str, str], UserCredentials],
        dict[tuple[DecodedDatabaseIdField, str], CredentialsGroup],
        dict[tuple[DecodedDatabaseIdField, str, bool], Credential],
    ]:
        """Creates index maps for quick lookup of existing credentials by unique keys."""
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


class UserCredentialsEnvironmentBuilder:
    def __init__(
        self,
        vault: Vault,
        session: scoped_session,
        user: User,
    ):
        self.vault = vault
        self.session = session
        self.user = user

    def build_environment_variables(
        self, source_type: str, source_id: str, requirements: list[CredentialsRequirement]
    ) -> list[dict[str, str]]:
        """
        Build environment variables for the given service requirements.

        Returns environment variables for all services that have credentials configured.
        Services without credentials are skipped, allowing tools to handle missing
        credentials or provide defaults.
        """
        env_variables: list[dict[str, str]] = []
        user_vault = UserVaultWrapper(self.vault, self.user)
        user_id = self.user.id

        for service in requirements:
            stmt = _build_user_credentials_query(
                user_id=user_id,
                source_type=source_type,
                source_id=source_id,
                service_name=service.name,
                service_version=service.version,
                current_group_only=True,
            )
            result = self.session.execute(stmt).tuples().all()

            if not result:
                # Skip this service if no credentials found - continue with other services
                continue

            current_group_id = result[0][1].id

            # Build maps for credentials and secrets that have been set by the user
            credential_value_map = {}
            set_secret_names = set()
            for _, _, c in result:
                if c is not None and c.is_set:
                    credential_value_map[c.name] = c.value
                    if c.is_secret:
                        set_secret_names.add(c.name)

            for secret in service.secrets:
                # Only read from vault if the secret has been set by the user
                if secret.name in set_secret_names:
                    vault_ref = build_vault_credential_reference(
                        source_type, source_id, service.name, service.version, current_group_id, secret.name
                    )
                    secret_value = user_vault.read_secret(vault_ref) or ""
                    env_variables.append({"name": secret.inject_as_env, "value": secret_value})

            for variable in service.variables:
                variable_value = str(credential_value_map.get(variable.name, ""))
                env_variables.append({"name": variable.inject_as_env, "value": variable_value})

        return env_variables
