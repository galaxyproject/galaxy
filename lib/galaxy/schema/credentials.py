from enum import Enum
from typing import (
    Dict,
    List,
    Optional,
)

from pydantic import (
    Field,
    RootModel,
)
from typing_extensions import Literal

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)
from galaxy.schema.schema import Model

SOURCE_TYPE = Literal["tool"]


class CredentialType(str, Enum):
    secret = "secret"
    variable = "variable"


class CredentialResponse(Model):
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="ID of the credential",
    )
    name: str = Field(
        ...,
        title="Credential Name",
        description="Name of the credential",
    )


class VariableResponse(CredentialResponse):
    value: Optional[str] = Field(
        None,
        title="Value",
        description="Value of the credential",
    )


class SecretResponse(CredentialResponse):
    already_set: bool = Field(
        ...,
        title="Already Set",
        description="Whether the secret is already set",
    )


class CredentialGroupResponse(Model):
    id: EncodedDatabaseIdField = Field(
        ...,
        title="Group ID",
        description="ID of the group",
    )
    name: str = Field(
        ...,
        title="Group Name",
        description="Name of the group",
    )
    variables: List[VariableResponse] = Field(
        ...,
        title="Variables",
        description="List of variables",
    )
    secrets: List[SecretResponse] = Field(
        ...,
        title="Secrets",
        description="List of secrets",
    )


class UserCredentialBaseResponse(Model):
    user_id: EncodedDatabaseIdField = Field(
        ...,
        title="User ID",
        description="ID of the user",
    )
    id: EncodedDatabaseIdField = Field(
        ...,
        title="User Credentials ID",
        description="ID of the user credentials",
    )
    source_type: SOURCE_TYPE = Field(
        ...,
        title="Source Type",
        description="Type of the source",
    )
    source_id: str = Field(
        ...,
        title="Source ID",
        description="ID of the source",
    )
    reference: str = Field(
        ...,
        title="Service Reference",
        description="Reference to the service",
    )
    current_group_name: str = Field(
        ...,
        title="Current Group Name",
        description="Name of the current group",
    )


class UserCredentialsResponse(UserCredentialBaseResponse):
    groups: Dict[str, CredentialGroupResponse] = Field(
        ...,
        title="Groups",
        description="Groups of credentials",
    )


class UserCredentialCreateResponse(UserCredentialBaseResponse):
    group: CredentialGroupResponse = Field(
        ...,
        title="Group",
        description="Group of credentials",
    )


class UserCredentialsListResponse(RootModel):
    root: List[UserCredentialsResponse] = Field(
        ...,
        title="User Credentials",
        description="List of user credentials",
    )


class CredentialPayload(Model):
    name: str = Field(
        ...,
        title="Credential Name",
        description="Name of the credential",
    )
    type: CredentialType = Field(
        ...,
        title="Type",
        description="Type of the credential(secret/variable)",
    )
    value: str = Field(
        ...,
        title="Credential Value",
        description="Value of the credential",
    )


class CredentialsPayload(Model):
    source_type: SOURCE_TYPE = Field(
        ...,
        title="Source Type",
        description="Type of the source",
    )
    source_id: str = Field(
        ...,
        title="Source ID",
        description="ID of the source",
    )
    reference: str = Field(
        ...,
        title="Service Reference",
        description="Reference to the service",
    )
    group_name: Optional[str] = Field(
        "default",
        title="Group Name",
        description="Name of the group",
    )
    credentials: List[CredentialPayload] = Field(
        ...,
        title="Credentials",
        description="List of credentials",
    )


class UpdateCredentialPayload(Model):
    id: DecodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="ID of the credential",
    )
    value: str = Field(
        ...,
        title="Value",
        description="Value of the credential",
    )


class UpdateCredentialsPayload(Model):
    group_id: DecodedDatabaseIdField = Field(
        ...,
        title="Group ID",
        description="ID of the group",
    )
    credentials: List[UpdateCredentialPayload] = Field(
        ...,
        title="Update Credentials",
        description="List of credentials to update",
    )
