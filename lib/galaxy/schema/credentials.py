from datetime import datetime
from typing import (
    Annotated,
    Literal,
    Optional,
)

from pydantic import (
    Field,
    RootModel,
)

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)
from galaxy.schema.schema import Model

SOURCE_TYPE = Literal["tool"]


class CredentialResponse(Model):
    name: Annotated[
        str,
        Field(
            description="The name of the credential.",
        ),
    ]


class VariableResponse(CredentialResponse):
    value: Annotated[
        Optional[str],
        Field(
            None,
            description="The value of the variable (for variables, not secrets).",
        ),
    ]


class SecretResponse(CredentialResponse):
    is_set: Annotated[
        bool,
        Field(
            description="Whether the secret has been set (value is not exposed).",
        ),
    ]


# TODO: ServiceCredentialsGroupResponse
class CredentialGroupResponse(Model):
    id: Annotated[
        EncodedDatabaseIdField,
        Field(
            description="Encoded ID of the credential group.",
        ),
    ]
    name: Annotated[
        str,
        Field(
            description="The name of the credential group.",
        ),
    ]
    variables: list[VariableResponse]
    secrets: list[SecretResponse]


class CredentialDefinitionResponse(Model):
    name: Annotated[
        str,
        Field(
            description="The name of the credential definition.",
        ),
    ]
    label: Annotated[
        str,
        Field(
            description="The human-readable label for the credential.",
        ),
    ]
    description: Annotated[
        str,
        Field(
            description="A description of what this credential is used for.",
        ),
    ]
    optional: Annotated[
        bool,
        Field(
            description="Whether this credential is optional or required.",
        ),
    ]


# TODO: Rename the class to UserSourceServicesResponse
class UserCredentialsResponse(Model):
    user_id: Annotated[
        EncodedDatabaseIdField,
        Field(
            description="The ID of the user who owns these credentials.",
        ),
    ]
    id: Annotated[
        EncodedDatabaseIdField,
        Field(
            description="The encoded ID of the user credentials.",
        ),
    ]
    source_type: Annotated[
        SOURCE_TYPE,
        Field(
            description="The type of source (e.g., 'tool').",
        ),
    ]
    source_id: Annotated[
        str,
        Field(
            description="The ID of the source (e.g., tool ID).",
        ),
    ]
    source_version: Annotated[
        str,
        Field(
            description="The version of the source.",
        ),
    ]
    name: Annotated[
        str,
        Field(
            description="The name of the service requiring credentials.",
        ),
    ]
    version: Annotated[
        str,
        Field(
            description="The version of the service.",
        ),
    ]
    current_group_id: Annotated[
        Optional[EncodedDatabaseIdField],
        Field(
            None,
            description="The ID of the currently active credential group.",
        ),
    ]
    update_time: Annotated[
        datetime,
        Field(
            description="The latest update time based on the most recently updated credential group.",
        ),
    ]
    groups: list[CredentialGroupResponse]


class UserCredentialsListResponse(RootModel):
    root: list[UserCredentialsResponse]


class ServiceCredentialsDefinition(Model):
    name: Annotated[
        str,
        Field(
            description="The name of the service.",
        ),
    ]
    version: Annotated[
        str,
        Field(
            description="The version of the service.",
        ),
    ]
    description: Annotated[
        str,
        Field(
            description="A description of the service.",
        ),
    ]
    label: Annotated[
        Optional[str],
        Field(
            None,
            description="A human-readable label for the service.",
        ),
    ]
    optional: Annotated[
        bool,
        Field(
            description="If true, tools can run without credentials; if false, credentials must be provided before execution.",
        ),
    ]
    variables: list[CredentialDefinitionResponse]
    secrets: list[CredentialDefinitionResponse]


class ExtendedUserCredentialsResponse(UserCredentialsResponse):
    definition: ServiceCredentialsDefinition


class ExtendedUserCredentialsListResponse(RootModel):
    root: list[ExtendedUserCredentialsResponse]


class CredentialPayload(Model):
    name: Annotated[
        str,
        Field(
            title="Credential Name",
            description="The name of the credential (variable or secret).",
        ),
    ]
    value: Annotated[
        Optional[str],
        Field(
            None,
            description="The value of the credential.",
        ),
    ]


class ServiceGroupPayload(Model):
    name: Annotated[
        str,
        Field(
            min_length=3,
            description="The name of the credential group (minimum 3 characters).",
        ),
    ]
    variables: Annotated[
        list[CredentialPayload],
        Field(
            description="List of variables for this credential group.",
        ),
    ]
    secrets: Annotated[
        list[CredentialPayload],
        Field(
            description="List of secrets for this credential group.",
        ),
    ]


class SourceCredentialPayload(Model):
    source_type: Annotated[
        SOURCE_TYPE,
        Field(
            description="The type of source requiring credentials.",
        ),
    ]
    source_id: Annotated[
        str,
        Field(
            description="The ID of the source (e.g., tool ID).",
        ),
    ]
    source_version: Annotated[
        str,
        Field(
            description="The version of the source.",
        ),
    ]


class ServiceCredentialPayload(Model):
    name: Annotated[
        str,
        Field(
            description="The name of the service requiring credentials.",
        ),
    ]
    version: Annotated[
        str,
        Field(
            description="The version of the service.",
        ),
    ]
    group: Annotated[
        ServiceGroupPayload,
        Field(
            description="The credential group containing variables and secrets.",
        ),
    ]


class CreateSourceCredentialsPayload(SourceCredentialPayload):
    service_credential: Annotated[
        ServiceCredentialPayload,
        Field(
            description="The service credential details including group and credentials.",
        ),
    ]


class SelectCurrentGroupPayload(Model):
    user_credentials_id: Annotated[
        DecodedDatabaseIdField,
        Field(
            description="The ID of the user credentials to update.",
        ),
    ]
    current_group_id: Annotated[
        Optional[DecodedDatabaseIdField],
        Field(
            None,
            description="The ID of the group to set as current (None to unset).",
        ),
    ]


class SelectServiceCredentialPayload(SourceCredentialPayload):
    service_credentials: Annotated[
        list[SelectCurrentGroupPayload],
        Field(
            description="List of user credentials to update with current group selections.",
        ),
    ]
