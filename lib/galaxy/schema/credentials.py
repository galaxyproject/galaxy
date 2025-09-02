from typing import (
    List,
    Optional,
)

from pydantic import RootModel
from typing_extensions import Literal

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)
from galaxy.schema.schema import Model

SOURCE_TYPE = Literal["tool"]


class CredentialResponse(Model):
    name: str


class VariableResponse(CredentialResponse):
    value: Optional[str]


class SecretResponse(CredentialResponse):
    is_set: bool


# TODO: ServiceCredentialsGroupResponse
class CredentialGroupResponse(Model):
    id: EncodedDatabaseIdField
    name: str
    variables: List[VariableResponse]
    secrets: List[SecretResponse]


class CredentialDefinitionResponse(Model):
    name: str
    label: str
    description: str
    optional: bool


# TODO: Rename the class to UserSourceServicesResponse
class UserCredentialsResponse(Model):
    user_id: EncodedDatabaseIdField
    id: EncodedDatabaseIdField
    source_type: SOURCE_TYPE
    source_id: str
    source_version: str
    name: str
    version: str
    current_group_id: Optional[EncodedDatabaseIdField] = None
    groups: List[CredentialGroupResponse]


class UserCredentialsListResponse(RootModel):
    root: List[UserCredentialsResponse]


class ExtendedUserCredentialsResponse(UserCredentialsResponse):
    label: str
    description: str
    variables: List[CredentialDefinitionResponse]
    secrets: List[CredentialDefinitionResponse]


class ExtendedUserCredentialsListResponse(RootModel):
    root: List[ExtendedUserCredentialsResponse]


class CredentialPayload(Model):
    name: str
    value: Optional[str]


class ServiceGroupPayload(Model):
    name: str
    variables: List[CredentialPayload]
    secrets: List[CredentialPayload]


class SourceCredentialPayload(Model):
    source_type: SOURCE_TYPE
    source_id: str
    source_version: str


class ServiceCredentialPayload(Model):
    name: str
    version: str
    group: ServiceGroupPayload


class CreateSourceCredentialsPayload(SourceCredentialPayload):
    service_credential: ServiceCredentialPayload


class SelectCurrentGroupPayload(Model):
    user_credentials_id: DecodedDatabaseIdField
    current_group_id: Optional[DecodedDatabaseIdField] = None


class SelectServiceCredentialPayload(SourceCredentialPayload):
    service_credentials: List[SelectCurrentGroupPayload]
