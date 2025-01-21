from typing import (
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import RootModel
from typing_extensions import Literal

from galaxy.model import (
    CredentialsGroup,
    Secret,
    UserCredentials,
    Variable,
)
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import Model

SOURCE_TYPE = Literal["tool"]


CredentialsModelList = List[Union[UserCredentials, CredentialsGroup, Variable, Secret]]


class CredentialResponse(Model):
    id: EncodedDatabaseIdField
    name: str


class VariableResponse(CredentialResponse):
    value: Optional[str]


class SecretResponse(CredentialResponse):
    already_set: bool


class CredentialGroupResponse(Model):
    id: EncodedDatabaseIdField
    name: str
    variables: List[VariableResponse]
    secrets: List[SecretResponse]


class UserCredentialsResponse(Model):
    user_id: EncodedDatabaseIdField
    id: EncodedDatabaseIdField
    source_type: SOURCE_TYPE
    source_id: str
    reference: str
    current_group_name: str
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


class ServiceCredentialPayload(Model):
    reference: str  # Reference to the service
    current_group: Optional[str] = "default"  # The selected group, the one that would be used when running the service
    groups: List[ServiceGroupPayload]  # All provided groups, including the selected one


class CreateSourceCredentialsPayload(Model):
    source_type: SOURCE_TYPE
    source_id: str
    credentials: List[ServiceCredentialPayload]  # The credentials to create for each service
