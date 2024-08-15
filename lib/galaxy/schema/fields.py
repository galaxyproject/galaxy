import re
from typing import (
    get_origin,
    TYPE_CHECKING,
    Union,
)

from pydantic import (
    BeforeValidator,
    Field,
    PlainSerializer,
    WithJsonSchema,
)
from typing_extensions import (
    Annotated,
    get_args,
)

if TYPE_CHECKING:
    from galaxy.security.idencoding import IdEncodingHelper

ENCODED_DATABASE_ID_PATTERN = re.compile("f?[0-9a-f]+")
ENCODED_ID_LENGTH_MULTIPLE = 16


class Security:
    security: "IdEncodingHelper"


def ensure_valid_id(v: str) -> str:
    assert isinstance(v, str)
    len_v = len(v)
    if len_v % ENCODED_ID_LENGTH_MULTIPLE:
        raise ValueError("Invalid id length, must be multiple of 16")
    m = ENCODED_DATABASE_ID_PATTERN.fullmatch(v.lower())
    if not m:
        raise ValueError("Invalid characters in encoded ID")
    return v


def ensure_valid_folder_id(v):
    if not isinstance(v, str):
        raise ValueError("String required")
    if not v.startswith("F"):
        raise ValueError("Invalid library folder ID. Folder IDs must start with an 'F'")
    v = v[1:]
    ensure_valid_id(v)
    return v


DecodedDatabaseIdField = Annotated[
    int,
    BeforeValidator(lambda database_id: Security.security.decode_id(database_id)),
    BeforeValidator(ensure_valid_id),
    PlainSerializer(lambda database_id: Security.security.encode_id(database_id), return_type=str, when_used="json"),
    WithJsonSchema(
        {"type": "string", "example": "0123456789ABCDEF", "pattern": "[0-9a-fA-F]+", "minLength": 16},
        mode="serialization",
    ),
    WithJsonSchema(
        {"type": "string", "example": "0123456789ABCDEF", "pattern": "[0-9a-fA-F]+", "minLength": 16},
        mode="validation",
    ),
]

EncodedDatabaseIdField = Annotated[
    str,
    BeforeValidator(lambda database_id: Security.security.encode_id(database_id)),
    WithJsonSchema(
        {"type": "string", "example": "0123456789ABCDEF", "pattern": "[0-9a-fA-F]+", "minLength": 16},
        mode="serialization",
    ),
    WithJsonSchema(
        {"type": "string", "example": "0123456789ABCDEF", "pattern": "[0-9a-fA-F]+", "minLength": 16},
        mode="validation",
    ),
]

LibraryFolderDatabaseIdField = Annotated[
    int,
    BeforeValidator(lambda database_id: Security.security.decode_id(database_id)),
    BeforeValidator(ensure_valid_folder_id),
    PlainSerializer(
        lambda database_id: f"F{Security.security.encode_id(database_id)}", return_type=str, when_used="json"
    ),
    WithJsonSchema(
        {"type": "string", "example": "0123456789ABCDEF", "pattern": "[0-9a-fA-F]+", "minLength": 16},
        mode="serialization",
    ),
    WithJsonSchema(
        {"type": "string", "example": "0123456789ABCDEF", "pattern": "[0-9a-fA-F]+", "minLength": 16},
        mode="validation",
    ),
]

EncodedLibraryFolderDatabaseIdField = Annotated[
    str,
    BeforeValidator(lambda database_id: f"F{Security.security.encode_id(database_id)}"),
    WithJsonSchema(
        {"type": "string", "example": "0123456789ABCDEF", "pattern": "[0-9a-fA-F]+", "minLength": 16},
        mode="serialization",
    ),
    WithJsonSchema(
        {"type": "string", "example": "0123456789ABCDEF", "pattern": "[0-9a-fA-F]+", "minLength": 16},
        mode="validation",
    ),
]


def literal_to_value(arg):
    val = get_args(arg)
    if not val:
        return arg
    if len(val) > 1:
        raise Exception("Can't extract default argument for unions")
    return val[0]


def is_optional(field):
    args = get_args(field)
    return get_origin(field) is Union and len(args) == 2 and type(None) in args


def ModelClassField(default_value):
    """Represents a database model class name annotated as a constant
    pydantic Field.
    :param class_name: The name of the database class.
    :return: A constant pydantic Field with default annotations for model classes.
    """
    return Field(
        ...,
        title="Model class",
        description="The name of the database model class.",
        json_schema_extra={"const": literal_to_value(default_value), "type": "string"},
    )


def accept_wildcard_defaults_to_json(v):
    assert isinstance(v, str)
    # Accept header can have multiple comma separated values.
    # If any of these values is the wildcard - we default to application/json.
    if "*/*" in v:
        return "application/json"
    return v


AcceptHeaderValidator = BeforeValidator(accept_wildcard_defaults_to_json)
