from typing import (
    Any,
    Callable,
    cast,
    Dict,
    Optional,
)

from galaxy.exceptions import (
    AuthenticationFailed,
    AuthenticationRequired,
    ItemOwnershipException,
    ObjectNotFound,
    RequestParameterInvalidException,
    ToolMetaParameterException,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.credentials import (
    CredentialsManager,
    CredentialsModelsList,
)
from galaxy.model import User
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
from galaxy.tool_util.deps.requirements import CredentialsRequirement
from galaxy.tools import Tool

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
    ) -> UserCredentialsListResponse:
        """Allows users to provide credentials for a group of secrets and variables."""
        user = self._ensure_user_access(trans, user_id)
        self._create_or_update_credentials(trans.sa_session, user, payload)
        return self._list_user_credentials(user, payload.source_type, payload.source_id, payload.source_version)

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
            user.id, user_credentials_id=user_credentials_id, group_id=group_id
        )
        if not existing_user_credentials:
            raise ObjectNotFound("No credentials found.")
        rows_to_delete: CredentialsModelsList = []
        for user_credentials, credentials_group, credential in existing_user_credentials:
            if group_id:
                if credentials_group.name == "default":
                    raise RequestParameterInvalidException("Cannot delete the default group.")
                if credentials_group.id == user_credentials.current_group_id:
                    self.credentials_manager.update_current_group(user.id, user_credentials.id, "default")
            else:
                rows_to_delete.append(user_credentials)
            rows_to_delete.extend([credentials_group, credential])
        self.credentials_manager.delete_rows(rows_to_delete)

    def _get_tool_credentials_definition(
        self,
        user: User,
        tool_id: str,
        tool_version: str,
        service_name: str,
        service_version: str,
    ) -> Optional[CredentialsRequirement]:
        tool: Tool = self.app.toolbox.get_tool(tool_id, tool_version)
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
                    "label": definition.label,
                    "description": definition.description,
                    "credential_definitions": {
                        "variables": [v.to_dict() for v in definition.variables],
                        "secrets": [s.to_dict() for s in definition.secrets],
                    },
                    "groups": {},
                },
            )

            user_credentials_dict[cred_id]["groups"].setdefault(
                credentials_group.name,
                {
                    "id": credentials_group.id,
                    "name": credentials_group.name,
                    "variables": [],
                    "secrets": [],
                },
            )

            target_list = "secrets" if credential.is_secret else "variables"
            user_credentials_dict[cred_id]["groups"][credentials_group.name][target_list].append(
                {
                    "id": credential.id,
                    "name": credential.name,
                    "is_set": credential.is_set,
                    "value": credential.value,
                }
            )

            if credentials_group.id == user_credentials.current_group_id:
                user_credentials_dict[cred_id]["current_group_name"] = credentials_group.name

        user_credentials_list = [UserCredentialsResponse(**cred) for cred in user_credentials_dict.values()]
        return UserCredentialsListResponse(root=user_credentials_list)

    def _create_or_update_credentials(
        self,
        session: galaxy_scoped_session,
        user: User,
        payload: CreateSourceCredentialsPayload,
    ) -> None:
        user_vault = UserVaultWrapper(self.app.vault, user)
        source_type, source_id, source_version = payload.source_type, payload.source_id, payload.source_version
        existing_user_credentials = self.credentials_manager.get_user_credentials(
            user.id, source_type, source_id, source_version
        )
        for service_payload in payload.credentials:
            service_name = service_payload.name
            service_version = service_payload.version
            source_credentials = self.source_type_credentials[source_type](
                user, source_id, source_version, service_name, service_version
            )
            if source_credentials is None:
                raise RequestParameterInvalidException(
                    f"Service '{service_name}' with version '{service_version}' is not defined"
                    f"in {source_type} with id {source_id} and version {source_version}."
                )
            user_credentials_id = self.credentials_manager.add_user_credentials(
                existing_user_credentials,
                user.id,
                source_type,
                source_id,
                source_version,
                service_name,
                service_version,
            )
            for group in service_payload.groups:
                user_credential_group_id = self.credentials_manager.add_group(
                    existing_user_credentials, user_credentials_id, group.name
                )
                for variable_payload in group.variables:
                    if not any(v.name == variable_payload.name for v in source_credentials.variables):
                        raise RequestParameterInvalidException(
                            f"Variable '{variable_payload.name}' is not defined for service '{service_name}'."
                        )
                    if variable_payload.value is not None:
                        self.credentials_manager.add_or_update_credential(
                            existing_user_credentials,
                            user_credential_group_id,
                            variable_payload.name,
                            variable_payload.value,
                        )
                for secret_payload in group.secrets:
                    if not any(s.name == secret_payload.name for s in source_credentials.secrets):
                        raise RequestParameterInvalidException(
                            f"Secret '{secret_payload.name}' is not defined for service '{service_name}'."
                        )
                    if secret_payload.value is not None:
                        vault_ref = f"{source_type}|{source_id}|{service_name}|{service_version}|{group.name}|{secret_payload.name}"
                        user_vault.write_secret(vault_ref, secret_payload.value)
                        self.credentials_manager.add_or_update_credential(
                            existing_user_credentials,
                            user_credential_group_id,
                            secret_payload.name,
                            secret_payload.value,
                            is_secret=True,
                        )
            self.credentials_manager.update_current_group(user.id, user_credentials_id, service_payload.current_group)
        session.commit()

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
