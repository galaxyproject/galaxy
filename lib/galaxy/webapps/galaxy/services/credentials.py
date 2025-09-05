from typing import (
    Any,
    Callable,
    cast,
    Optional,
    Union,
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
    CredentialsAssociation,
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
    ExtendedUserCredentialsListResponse,
    ExtendedUserCredentialsResponse,
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
        self.source_type_credentials: dict[SOURCE_TYPE, GetToolCredentialsDefinition] = {
            "tool": self._get_tool_credentials_definition,
        }

    def list_user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
        source_type: Optional[SOURCE_TYPE] = None,
        source_id: Optional[str] = None,
        source_version: Optional[str] = None,
        include_definition: bool = False,
    ) -> Union[UserCredentialsListResponse, ExtendedUserCredentialsListResponse]:
        """Lists all credentials the user has provided (credentials themselves are not included)."""
        user = self._ensure_user_access(trans, user_id)
        return self._list_user_credentials(user, source_type, source_id, source_version, include_definition)

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

        cred_map: dict[DecodedDatabaseIdField, UserCredentials] = {}
        group_map: dict[DecodedDatabaseIdField, UserCredentials] = {}
        for uc, cg, _ in existing_user_credentials:
            cred_map[uc.id] = uc
            group_map[cg.id] = uc

        updated_credentials: set[UserCredentials] = set()

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
        secrets_to_delete: set[str] = set()

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
                            self._build_vault_credential_reference(
                                user_credentials, credentials_group.id, credential.name
                            )
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
                        self._build_vault_credential_reference(user_credentials, credentials_group.id, credential.name)
                    )

        if secrets_to_delete:
            user_vault = UserVaultWrapper(self.app.vault, user)
            for vault_ref in secrets_to_delete:
                user_vault.delete_secret(vault_ref)

        self.credentials_manager.delete_rows(rows_to_delete)

    def _build_vault_credential_reference(
        self, user_credentials: UserCredentials, group_id: int, secret_name: str
    ) -> str:
        return f"{user_credentials.source_type}|{user_credentials.source_id}|{user_credentials.name}|{user_credentials.version}|{group_id}|{secret_name}"

    def _get_credentials_definition(
        self,
        user: User,
        source_type: SOURCE_TYPE,
        source_id: str,
        source_version: str,
        service_name: str,
        service_version: str,
    ) -> CredentialsRequirement:
        definition = self.source_type_credentials[source_type](
            user, source_id, source_version, service_name, service_version
        )
        if definition is None:
            raise ObjectNotFound(
                f"Service '{service_name}' with version '{service_version}' is not defined "
                f"in {source_type} with id {source_id} and version {source_version}."
            )
        return definition

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
        include_definition: bool = False,
    ) -> Union[UserCredentialsListResponse, ExtendedUserCredentialsListResponse]:
        existing_user_credentials = self.credentials_manager.get_user_credentials(
            user.id, source_type, source_id, source_version
        )
        user_credentials_dict: dict[int, dict[str, Any]] = {}
        groups_dict: dict[tuple[int, int], dict[str, Any]] = {}

        for user_credentials, credentials_group, credential in existing_user_credentials:
            cred_id = user_credentials.id
            definition = self._get_credentials_definition(
                user,
                cast(SOURCE_TYPE, user_credentials.source_type),
                user_credentials.source_id,
                user_credentials.source_version,
                user_credentials.name,
                user_credentials.version,
            )
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
                    "current_group_id": user_credentials.current_group_id,
                    "groups": [],
                },
            )

            if include_definition:
                user_credentials_dict[cred_id]["definition"] = {
                    "name": definition.name,
                    "version": definition.version,
                    "description": definition.description,
                    "label": definition.label,
                    "variables": [v.to_dict() for v in definition.variables],
                    "secrets": [s.to_dict() for s in definition.secrets],
                }

            group_key = (cred_id, credentials_group.id)
            groups_dict.setdefault(
                group_key,
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
            groups_dict[group_key][target_list].append(entry)

        # Convert groups from dictionary to list for each user credentials
        for cred_id, cred_data in user_credentials_dict.items():
            cred_data["groups"] = [
                CredentialGroupResponse(**group_data)
                for (c_id, g_id), group_data in groups_dict.items()
                if c_id == cred_id
            ]

        if include_definition:
            extended_user_credentials_list = [
                ExtendedUserCredentialsResponse(**cred) for cred in user_credentials_dict.values()
            ]
            return ExtendedUserCredentialsListResponse(root=extended_user_credentials_list)
        else:
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

        user_credentials, credentials_group = next((uc, cg) for uc, cg, _ in existing_user_credentials)
        if credentials_group.name != group_name:
            self.credentials_manager.update_group(credentials_group, group_name)

        existing_credentials_map: dict[tuple[str, bool], Credential] = {}
        for *_, credential in existing_user_credentials:
            existing_credentials_map[(credential.name, credential.is_secret)] = credential

        source_credentials = self._get_credentials_definition(
            user,
            cast(SOURCE_TYPE, user_credentials.source_type),
            user_credentials.source_id,
            user_credentials.source_version,
            user_credentials.name,
            user_credentials.version,
        )
        self._validate_credentials_against_definition(
            source_credentials, variables, secrets, user_credentials.name, is_update=True
        )

        for variable_payload in variables:
            variable_name, variable_value = variable_payload.name, variable_payload.value
            variable = existing_credentials_map.get((variable_name, False))
            if variable:
                self.credentials_manager.update_credential(variable, variable_value)
            else:
                raise ObjectNotFound(f"Variable '{variable_name}' not found.")

        user_vault = UserVaultWrapper(self.app.vault, user)
        for secret_payload in secrets:
            secret_name, secret_value = secret_payload.name, secret_payload.value
            secret = existing_credentials_map.get((secret_name, True))
            if secret:
                vault_ref = self._build_vault_credential_reference(user_credentials, credentials_group.id, secret_name)
                if secret_value is not None:
                    user_vault.write_secret(vault_ref, secret_value)
                    self.credentials_manager.update_credential(secret, secret_value, is_secret=True)
            else:
                raise ObjectNotFound(f"Secret '{secret_name}' not found.")

        session.commit()

        updated_credentials = self.credentials_manager.get_user_credentials(user.id, group_id=group_id)
        return self._construct_credential_group_response(group_id, group_name, updated_credentials)

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

        source_credentials = self._get_credentials_definition(
            user, source_type, source_id, source_version, service_name, service_version
        )
        self._validate_credentials_against_definition(source_credentials, variables, secrets, service_name)

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

            if (user_credential_group_id, variable_name, False) in cred_map:
                raise Conflict(f"Variable '{variable_name}' already exists in group '{group_name}'.")
            self.credentials_manager.add_credential(user_credential_group_id, variable_name, variable_value)

        user_vault = UserVaultWrapper(self.app.vault, user)
        for secret_payload in secrets:
            secret_name, secret_value = secret_payload.name, secret_payload.value

            if (user_credential_group_id, secret_name, True) in cred_map:
                raise Conflict(f"Secret '{secret_name}' already exists in group '{group_name}'.")
            if secret_value is not None:
                vault_ref = f"{source_type}|{source_id}|{service_name}|{service_version}|{user_credential_group_id}|{secret_name}"
                user_vault.write_secret(vault_ref, secret_value)
            self.credentials_manager.add_credential(
                user_credential_group_id,
                secret_name,
                secret_value,
                is_secret=True,
            )

        session.commit()

        updated_credentials = self.credentials_manager.get_user_credentials(
            user.id, user_credentials_id=user_credentials_id, group_id=user_credential_group_id
        )
        return self._construct_credential_group_response(
            user_credential_group_id,
            group_name,
            updated_credentials,
        )

    def _construct_credential_group_response(
        self,
        group_id: int,
        group_name: str,
        group_credentials: CredentialsAssociation,
    ) -> CredentialGroupResponse:
        updated_variables = []
        updated_secrets = []
        for *_, credential in group_credentials:
            if credential.is_secret:
                updated_secrets.append(
                    {
                        "name": credential.name,
                        "is_set": credential.is_set,
                    }
                )
            else:
                updated_variables.append(
                    {
                        "name": credential.name,
                        "value": credential.value,
                    }
                )

        group_data = {
            "id": group_id,
            "name": group_name,
            "variables": updated_variables,
            "secrets": updated_secrets,
        }
        return CredentialGroupResponse(**group_data)

    def _validate_credentials_against_definition(
        self,
        source_credentials: CredentialsRequirement,
        variables: list[CredentialPayload],
        secrets: list[CredentialPayload],
        service_name: str,
        is_update: bool = False,
    ) -> None:
        defined_variables = {v.name: v for v in source_credentials.variables}
        defined_secrets = {s.name: s for s in source_credentials.secrets}
        provided_variables = {v.name for v in variables}
        provided_secrets = {s.name for s in secrets}
        for variable_payload in variables:
            variable_name = variable_payload.name
            variable_definition = defined_variables.get(variable_name)
            if not variable_definition:
                raise RequestParameterInvalidException(
                    f"Variable '{variable_name}' is not defined for service '{service_name}'."
                )
            if not variable_definition.optional and not variable_payload.value:
                raise RequestParameterInvalidException(
                    f"Required variable '{variable_name}' cannot be empty for service '{service_name}'."
                )
        for secret_payload in secrets:
            secret_name = secret_payload.name
            secret_definition = defined_secrets.get(secret_name)
            if not secret_definition:
                raise RequestParameterInvalidException(
                    f"Secret '{secret_name}' is not defined for service '{service_name}'."
                )
            # none value on secret means no update
            is_missing_value = not secret_payload.value if not is_update else secret_payload.value == ""
            if not secret_definition.optional and is_missing_value:
                raise RequestParameterInvalidException(
                    f"Required secret '{secret_name}' cannot be empty for service '{service_name}'."
                )
        for required_variable in source_credentials.variables:
            if not required_variable.optional and required_variable.name not in provided_variables:
                raise RequestParameterInvalidException(
                    f"Required variable '{required_variable.name}' is not provided for service '{service_name}'."
                )
        for required_secret in source_credentials.secrets:
            if not required_secret.optional and required_secret.name not in provided_secrets:
                raise RequestParameterInvalidException(
                    f"Required secret '{required_secret.name}' is not provided for service '{service_name}'."
                )

    def _ensure_user_access(
        self,
        trans: ProvidesUserContext,
        user_id: FlexibleUserIdType,
    ) -> User:
        if trans.anonymous:
            raise AuthenticationRequired("You need to be logged in to access your credentials.")
        assert trans.user is not None
        if user_id != "current" and user_id != trans.user.id:
            raise ItemOwnershipException("You can only access your own credentials.")
        return trans.user
