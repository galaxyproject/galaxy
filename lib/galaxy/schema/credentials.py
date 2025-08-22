from typing import (
    Dict,
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
    id: EncodedDatabaseIdField
    name: str
    is_set: bool
    value: Optional[str]


class CredentialGroupResponse(Model):
    id: EncodedDatabaseIdField
    name: str
    variables: List[CredentialResponse]
    secrets: List[CredentialResponse]


class CredentialDefinitionResponse(Model):
    name: str
    label: str
    description: str
    optional: bool


class CredentialDefinitionsResponse(Model):
    variables: List[CredentialDefinitionResponse]
    secrets: List[CredentialDefinitionResponse]


class UserCredentialsResponse(Model):
    user_id: EncodedDatabaseIdField
    id: EncodedDatabaseIdField
    source_type: SOURCE_TYPE
    source_id: str
    source_version: str
    name: str
    version: str
    label: str
    description: str
    current_group_name: Optional[str] = None
    current_group_id: Optional[EncodedDatabaseIdField] = None
    credential_definitions: CredentialDefinitionsResponse
    groups: Dict[str, CredentialGroupResponse]


class UserCredentialsListResponse(RootModel):
    root: List[UserCredentialsResponse]


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
