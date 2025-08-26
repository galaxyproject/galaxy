from typing import (
    Any,
    Callable,
    cast,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
)

from galaxy.exceptions import (
    AuthenticationFailed,
    AuthenticationRequired,
    Conflict,
    ItemOwnershipException,
    ObjectNotFound,
    RequestParameterInvalidException,
    ToolMetaParameterException,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.credentials import (
    CredentialsManager,
    CredentialsModelsSet,
)
from galaxy.model import (
    Credential,
    User,
    UserCredentials,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.credentials import (
    CreateSourceCredentialsPayload,
    CredentialGroupResponse,
    CredentialPayload,
    SelectServiceCredentialPayload,
    ServiceGroupPayload,
    SOURCE_TYPE,
    UserCredentialsListResponse,
    UserCredentialsResponse,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import FlexibleUserIdType
from galaxy.security.vault import UserVaultWrapper
from galaxy.structured_app import StructuredApp
from galaxy.tool_util.deps.requirements import CredentialsRequirement

GetToolCredentialsDefinition = Callable[[User, str, str, str, str], Optional[CredentialsRequirement]]


class CredentialsService:
    """Service object shared by controllers for interacting with credentials."""

    def __init__(
        self,
        app: StructuredApp,
        credentials_manager: CredentialsManager,
    ) -> None:
        self.app = app
        self.credentials_manager = credentials_manager
        self.source_type_credentials: Dict[SOURCE_TYPE, GetToolCredentialsDefinition] = {
            "tool": self._get_tool_credentials_definition,
        }

    def list_user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
        source_version: Optional[str] = None,
    ) -> UserCredentialsListResponse:
        """Lists all credentials the user has provided (credentials themselves are not included)."""
        user = self._ensure_user_access(trans, user_id)
        return self._list_user_credentials(user, source_type, source_id, source_version)

    def provide_credential(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        payload: CreateSourceCredentialsPayload,
    ) -> CredentialGroupResponse:
        """Allows users to provide credentials for a group of secrets and variables."""
        user = self._ensure_user_access(trans, user_id)
        credentials = self._create_credentials(trans.sa_session, user, payload)
        return credentials

    def update_user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        group_id: DecodedDatabaseIdField,
        payload: ServiceGroupPayload,
    ) -> CredentialGroupResponse:
        """Updates user credentials for a specific group."""
        user = self._ensure_user_access(trans, user_id)
        return self._update_credentials(trans.sa_session, user, group_id, payload)

    def update_user_credentials_group(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        payload: SelectServiceCredentialPayload,
    ) -> None:
        """Updates user credentials for a specific group."""
        user = self._ensure_user_access(trans, user_id)

        source_type, source_id, source_version, service_credentials = (
            payload.source_type,
            payload.source_id,
            payload.source_version,
            payload.service_credentials,
        )

        existing_user_credentials = self.credentials_manager.get_user_credentials(
            user.id, source_type=source_type, source_id=source_id, source_version=source_version
        )

        if not existing_user_credentials:
            raise ObjectNotFound(f"No credentials found for {source_type}, {source_id}, {source_version}")

        cred_map: Dict[DecodedDatabaseIdField, UserCredentials] = {}
        group_map: Dict[DecodedDatabaseIdField, UserCredentials] = {}
        for uc, cg, _ in existing_user_credentials:
            cred_map[uc.id] = uc
            group_map[cg.id] = uc

        updated_credentials: Set[UserCredentials] = set()

        for service in service_credentials:
            if service.current_group_id is not None:
                user_credentials = group_map.get(service.current_group_id)
            else:
                user_credentials = cred_map.get(service.user_credentials_id)

            if not user_credentials:
                raise ObjectNotFound("No user credentials found.")

            if user_credentials.current_group_id != service.current_group_id:
                self.credentials_manager.update_current_group(user_credentials, service.current_group_id)
                updated_credentials.add(user_credentials)
        if updated_credentials:
            trans.sa_session.commit()

    def delete_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        user_credentials_id: Optional[DecodedDatabaseIdField] = None,
        group_id: Optional[DecodedDatabaseIdField] = None,
    ) -> None:
        """Deletes a specific credential group or all credentials for a specific service."""
        user = self._ensure_user_access(trans, user_id)
        existing_user_credentials = self.credentials_manager.get_user_credentials(
            user.id, user_credentials_id=user_credentials_id
        )
        if not existing_user_credentials:
            raise ObjectNotFound("No credentials found.")

        rows_to_delete: CredentialsModelsSet = set()
        secrets_to_delete: Set[str] = set()

        if group_id:
            user_credentials_record = None
            groups_for_service = set()
            group_found = False

            for user_credentials, credentials_group, credential in existing_user_credentials:
                user_credentials_record = user_credentials
                groups_for_service.add(credentials_group.id)

                if credentials_group.id == group_id:
                    group_found = True
                    rows_to_delete.update({credentials_group, credential})
                    if credential.is_secret:
                        secrets_to_delete.add(
                            f"{user_credentials.source_type}|{user_credentials.source_id}|{user_credentials.name}|{user_credentials.version}|{credentials_group.name}|{credential.name}"
                        )
                    if credentials_group.id == user_credentials.current_group_id:
                        self.credentials_manager.update_current_group(user_credentials, None)

            if not group_found:
                raise ObjectNotFound("No credentials found.")

            if not (groups_for_service - {group_id}) and user_credentials_record:
                rows_to_delete.add(user_credentials_record)

        else:
            for user_credentials, credentials_group, credential in existing_user_credentials:
                rows_to_delete.update({user_credentials, credentials_group, credential})
                if credential.is_secret:
                    secrets_to_delete.add(
                        f"{user_credentials.source_type}|{user_credentials.source_id}|{user_credentials.name}|{user_credentials.version}|{credentials_group.name}|{credential.name}"
                    )

        if secrets_to_delete:
            user_vault = UserVaultWrapper(self.app.vault, user)
            for vault_ref in secrets_to_delete:
                user_vault.delete_secret(vault_ref)

        self.credentials_manager.delete_rows(rows_to_delete)

    def _get_tool_credentials_definition(
        self,
        user: User,
        tool_id: str,
        tool_version: str,
        service_name: str,
        service_version: str,
    ) -> Optional[CredentialsRequirement]:
        tool = self.app.toolbox.get_tool(tool_id, tool_version)
        if not tool:
            raise ObjectNotFound(f"Could not find tool with id '{tool_id}'.")
        if not tool.allow_user_access(user):
            raise AuthenticationFailed(f"Access denied, please login for tool with id '{tool_id}'.")
        # even if the tool is found, the version might not be the same
        if tool.version != tool_version:
            raise ObjectNotFound(f"Could not find tool {tool_id} with version '{tool_version}'.")
        if not tool.credentials:
            raise ToolMetaParameterException(f"Tool '{tool_id}' does not require any credentials.")
        for credentials_service in tool.credentials:
            if credentials_service.name == service_name and credentials_service.version == service_version:
                return credentials_service
        return None

    def _list_user_credentials(
        self,
        user: User,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
        source_version: Optional[str] = None,
    ) -> UserCredentialsListResponse:
        existing_user_credentials = self.credentials_manager.get_user_credentials(
            user.id, source_type, source_id, source_version
        )
        user_credentials_dict: Dict[int, Dict[str, Any]] = {}
        for user_credentials, credentials_group, credential in existing_user_credentials:
            cred_id = user_credentials.id
            definition = self.source_type_credentials[cast(SOURCE_TYPE, user_credentials.source_type)](
                user,
                user_credentials.source_id,
                user_credentials.source_version,
                user_credentials.name,
                user_credentials.version,
            )
            if definition is None:
                continue
            user_credentials_dict.setdefault(
                cred_id,
                {
                    "user_id": user_credentials.user_id,
                    "id": cred_id,
                    "source_type": user_credentials.source_type,
                    "source_id": user_credentials.source_id,
                    "source_version": user_credentials.source_version,
                    "name": user_credentials.name,
                    "version": user_credentials.version,
                    "groups": {},
                },
            )

            user_credentials_dict[cred_id]["groups"].setdefault(
                # TODO: The id should be encoded
                credentials_group.id,
                {
                    "id": credentials_group.id,
                    "name": credentials_group.name,
                    "variables": [],
                    "secrets": [],
                },
            )

            if credential.is_secret:
                entry = {
                    "name": credential.name,
                    "is_set": credential.is_set,
                }
            else:
                entry = {
                    "name": credential.name,
                    "value": credential.value,
                }
            target_list = "secrets" if credential.is_secret else "variables"
            # TODO: The id should be encoded
            user_credentials_dict[cred_id]["groups"][credentials_group.id][target_list].append(entry)

        user_credentials_list = [UserCredentialsResponse(**cred) for cred in user_credentials_dict.values()]
        return UserCredentialsListResponse(root=user_credentials_list)

    def _update_credentials(
        self,
        session: galaxy_scoped_session,
        user: User,
        group_id: DecodedDatabaseIdField,
        payload: ServiceGroupPayload,
    ) -> CredentialGroupResponse:
        group_name, variables, secrets = payload.name, payload.variables, payload.secrets
        existing_user_credentials = self.credentials_manager.get_user_credentials(user.id, group_id=group_id)
        if not existing_user_credentials:
            raise ObjectNotFound(f"No credentials found for user {user.id} in group {group_id}.")

        user_vault = UserVaultWrapper(self.app.vault, user)

        user_credentials, credentials_group = next((uc, cg) for uc, cg, _ in existing_user_credentials)
        prefix_secret_ref = f"{user_credentials.source_type}|{user_credentials.source_id}|{user_credentials.name}|{user_credentials.version}"
        old_group_name = credentials_group.name
        if old_group_name != group_name:
            self.credentials_manager.update_group(credentials_group, group_name)

        existing_credentials_map: Dict[Tuple[str, bool], Credential] = {}
        for *_, credential in existing_user_credentials:
            existing_credentials_map[(credential.name, credential.is_secret)] = credential

        for variable_payload in variables:
            variable_name, variable_value = variable_payload.name, variable_payload.value
            variable = existing_credentials_map.get((variable_name, False))
            if variable:
                self.credentials_manager.update_credential(variable, variable_value)
            else:
                raise ObjectNotFound(f"Variable '{variable_name}' not found.")

        for secret_payload in secrets:
            secret_name, secret_value = secret_payload.name, secret_payload.value
            secret = existing_credentials_map.get((secret_name, True))
            if secret:
                old_group_secret = None
                if old_group_name != group_name:
                    old_vault_ref = f"{prefix_secret_ref}|{old_group_name}|{secret_name}"
                    old_group_secret = user_vault.read_secret(old_vault_ref)
                    user_vault.delete_secret(old_vault_ref)
                vault_ref = f"{prefix_secret_ref}|{group_name}|{secret_name}"
                if secret_value is not None:
                    user_vault.write_secret(vault_ref, secret_value)
                elif old_group_secret:
                    user_vault.write_secret(vault_ref, old_group_secret)
                self.credentials_manager.update_credential(secret, secret_value, is_secret=True)
            else:
                raise ObjectNotFound(f"Secret '{secret_name}' not found.")

        session.commit()

        return self._build_credential_group_response(group_id, group_name, variables, secrets)

    def _create_credentials(
        self,
        session: galaxy_scoped_session,
        user: User,
        payload: CreateSourceCredentialsPayload,
    ) -> CredentialGroupResponse:
        source_type, source_id, source_version, service = (
            payload.source_type,
            payload.source_id,
            payload.source_version,
            payload.service_credential,
        )
        service_name, service_version, service_group = service.name, service.version, service.group
        group_name, variables, secrets = service_group.name, service_group.variables, service_group.secrets

        source_credentials = self.source_type_credentials[source_type](
            user, source_id, source_version, service_name, service_version
        )
        if source_credentials is None:
            raise ObjectNotFound(
                f"Service '{service_name}' with version '{service_version}' is not defined "
                f"in {source_type} with id {source_id} and version {source_version}."
            )

        existing_user_credentials = self.credentials_manager.get_user_credentials(
            user.id, source_type, source_id, source_version
        )

        user_cred_map, group_map, cred_map = self.credentials_manager.index_credentials(existing_user_credentials)

        user_credentials = user_cred_map.get((service_name, service_version))
        if user_credentials:
            user_credentials_id = user_credentials.id
        else:
            user_credentials_id = self.credentials_manager.add_user_credentials(
                user.id,
                source_type,
                source_id,
                source_version,
                service_name,
                service_version,
            )

        if (user_credentials_id, group_name) in group_map:
            raise Conflict(f"Group '{group_name}' already exists.")
        user_credential_group_id = self.credentials_manager.add_group(user_credentials_id, group_name)

        for variable_payload in variables:
            variable_name, variable_value = variable_payload.name, variable_payload.value

            if not any(v.name == variable_name for v in source_credentials.variables):
                raise RequestParameterInvalidException(
                    f"Variable '{variable_name}' is not defined for service '{service_name}'."
                )
            if (user_credential_group_id, variable_name, False) in cred_map:
                raise Conflict(f"Variable '{variable_name}' already exists in group '{group_name}'.")
            self.credentials_manager.add_credential(user_credential_group_id, variable_name, variable_value)

        user_vault = UserVaultWrapper(self.app.vault, user)
        for secret_payload in secrets:
            secret_name, secret_value = secret_payload.name, secret_payload.value

            if not any(s.name == secret_name for s in source_credentials.secrets):
                raise RequestParameterInvalidException(
                    f"Secret '{secret_name}' is not defined for service '{service_name}'."
                )
            if (user_credential_group_id, secret_name, True) in cred_map:
                raise Conflict(f"Secret '{secret_name}' already exists in group '{group_name}'.")
            if secret_value is not None:
                vault_ref = f"{source_type}|{source_id}|{service_name}|{service_version}|{group_name}|{secret_name}"
                user_vault.write_secret(vault_ref, secret_value)
            self.credentials_manager.add_credential(
                user_credential_group_id,
                secret_name,
                secret_value,
                is_secret=True,
            )

        session.commit()

        return self._build_credential_group_response(
            user_credential_group_id,
            group_name,
            variables,
            secrets,
        )

    def _build_credential_group_response(
        self,
        group_id: DecodedDatabaseIdField,
        group_name: str,
        variables: List[CredentialPayload],
        secrets: List[CredentialPayload],
    ) -> CredentialGroupResponse:
        """Build a CredentialGroupResponse from variables and secrets data."""
        variables_list = []
        secrets_list = []

        for variable in variables:
            variable_name = variable.name
            variable_value = variable.value
            variables_list.append(
                {
                    "name": variable_name,
                    "value": variable_value,
                }
            )

        for secret in secrets:
            secret_name = secret.name
            secret_value = secret.value
            secrets_list.append(
                {
                    "name": secret_name,
                    "is_set": secret_value is not None,
                }
            )

        return CredentialGroupResponse(id=group_id, name=group_name, variables=variables_list, secrets=secrets_list)

    def _ensure_user_access(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
    ) -> User:
        if trans.anonymous:
            raise AuthenticationRequired("You need to be logged in to access your credentials.")
        if user_id != "current" and user_id != trans.user.id:
            raise ItemOwnershipException("You can only access your own credentials.")
        return trans.user
