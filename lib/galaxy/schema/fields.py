import re

from pydantic import PositiveInt

from galaxy.model import (
    get_id_encoding_helper,
)

ENCODED_DATABASE_ID_PATTERN = re.compile('f?[0-9a-f]+')
ENCODED_ID_LENGTH_MULTIPLE = 16


def encode_id(v: int):
    security = get_id_encoding_helper()
    return security.encode_id(v)


def decode_id(v: int):
    security = get_id_encoding_helper()
    return security.decode_id(v)


class DatabaseIdField(PositiveInt):
    """Database primary id for a model."""

    @classmethod
    def __get_validators__(cls):
        # one or more validators may be yielded which will be called in the
        # order to validate the input, each validator will receive as an input
        # the value returned from the previous validator
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, EncodedDatabaseIdField):
            v = decode_id(v)
        return cls(v)


class EncodedDatabaseIdField(str):
    """
    Encoded Database ID validation.
    """

    @classmethod
    def __get_validators__(cls):
        # one or more validators may be yielded which will be called in the
        # order to validate the input, each validator will receive as an input
        # the value returned from the previous validator
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema):
        # __modify_schema__ should mutate the dict it receives in place,
        # the returned value will be ignored
        field_schema.update(
            min_length=16,
            pattern='[0-9a-fA-F]+',
            examples=['0123456789ABCDEF'],
        )

    @classmethod
    def validate(cls, v):
        if isinstance(v, int):
            v = encode_id(v)
        if not isinstance(v, str):
            raise TypeError('String required')
        if v.startswith("F"):
            # Library Folder ids start with an additional "F"
            len_v = len(v) - 1
        else:
            len_v = len(v)
        if len_v % ENCODED_ID_LENGTH_MULTIPLE:
            raise ValueError('Invalid id length, must be multiple of 16')
        m = ENCODED_DATABASE_ID_PATTERN.fullmatch(v.lower())
        if not m:
            raise ValueError('Invalid characters in encoded ID')
        return cls(v)

    def __repr__(self):
        return f'EncodedDatabaseID ({super().__repr__()})'
