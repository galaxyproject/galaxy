from enum import Enum
from typing import List

from pydantic import (
    Field,
    RootModel,
)

from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import Model


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
    type: CredentialType = Field(
        ...,
        title="Type",
        description="Type of the credential",
    )


class CredentialsListResponse(Model):
    service_reference: str = Field(
        ...,
        title="Service Reference",
        description="Reference to the service",
    )
    user_credentials_id: EncodedDatabaseIdField = Field(
        ...,
        title="User Credentials ID",
        description="ID of the user credentials",
    )
    credentials: List[CredentialResponse] = Field(
        ...,
        title="Credentials",
        description="List of credentials",
    )


class UserCredentialsListResponse(RootModel):
    root: List[CredentialsListResponse] = Field(
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
    service_reference: str = Field(
        ...,
        title="Service Reference",
        description="Reference to the service",
    )
    credentials: List[CredentialPayload] = Field(
        ...,
        title="Credentials",
        description="List of credentials",
    )


class VerifyCredentialsResponse(Model):
    exists: bool = Field(
        ...,
        title="Exists",
        description="Indicates if the credentials exist",
    )


class DeleteCredentialsResponse(Model):
    deleted: bool = Field(
        ...,
        title="Deleted",
        description="Indicates if the credentials were deleted",
    )
