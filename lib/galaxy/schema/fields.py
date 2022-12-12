import re

from pydantic import Field
from typing_extensions import get_args

from galaxy.security.idencoding import IdEncodingHelper

ENCODED_DATABASE_ID_PATTERN = re.compile("f?[0-9a-f]+")
ENCODED_ID_LENGTH_MULTIPLE = 16


class BaseDatabaseIdField:
    """
    Database ID validation.
    """

    security: IdEncodingHelper

    @classmethod
    def __get_validators__(cls):
        # one or more validators may be yielded which will be called in the
        # order to validate the input, each validator will receive as an input
        # the value returned from the previous validator
        yield cls.validate

    @classmethod
    def validate(cls, v):
        return v

    @classmethod
    def ensure_valid(cls, v: str):
        len_v = len(v)
        if len_v % ENCODED_ID_LENGTH_MULTIPLE:
            raise ValueError("Invalid id length, must be multiple of 16")
        m = ENCODED_DATABASE_ID_PATTERN.fullmatch(v.lower())
        if not m:
            raise ValueError("Invalid characters in encoded ID")

    @classmethod
    def __modify_schema__(cls, field_schema):
        # __modify_schema__ should mutate the dict it receives in place,
        # the returned value will be ignored
        field_schema.update(
            minLength=16,
            pattern="[0-9a-fA-F]+",
            example=["0123456789ABCDEF"],
            type="string",
        )

    def __repr__(self):
        return f"DatabaseID ({super().__repr__()})"


class DecodedDatabaseIdField(int, BaseDatabaseIdField):
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError("String required")
        cls.ensure_valid(v)
        return cls(cls.security.decode_id(v))

    @classmethod
    def encode(cls, v) -> str:
        return cls.security.encode_id(v)


class LibraryFolderDatabaseIdField(int, BaseDatabaseIdField):
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError("String required")
        if not v.startswith("F"):
            raise TypeError("Invalid library folder ID. Folder IDs must start with an 'F'")
        v = v[1:]
        cls.ensure_valid(v)
        return cls(cls.security.decode_id(v))

    @classmethod
    def encode(cls, v) -> str:
        return f"F{cls.security.encode_id(v)}"


class EncodedDatabaseIdField(str, BaseDatabaseIdField):
    @classmethod
    def validate(cls, v):
        if isinstance(v, int):
            return cls(cls.security.encode_id(v))
        if not isinstance(v, str):
            raise TypeError("String required")
        cls.ensure_valid(v)
        return cls(v)

    @classmethod
    def decode(cls, v) -> int:
        return cls.security.decode_id(v)


def literal_to_value(arg):
    val = get_args(arg)
    if not val:
        return arg
    if len(val) > 1:
        raise Exception("Can't extract default argument for unions")
    return val[0]


def ModelClassField(default_value=...):
    """Represents a database model class name annotated as a constant
    pydantic Field.
    :param class_name: The name of the database class.
    :return: A constant pydantic Field with default annotations for model classes.
    """
    return Field(
        literal_to_value(default_value),
        title="Model class",
        description="The name of the database model class.",
        const=True,
        mark_required_in_schema=True,
    )
