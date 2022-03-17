import inspect
import re
from typing import Optional

from pydantic import (
    BaseModel,
    Field,
)

from galaxy.security.idencoding import IdEncodingHelper

ENCODED_DATABASE_ID_PATTERN = re.compile('f?[0-9a-f]+')
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
    def __modify_schema__(cls, field_schema):
        # __modify_schema__ should mutate the dict it receives in place,
        # the returned value will be ignored
        field_schema.update(
            min_length=16,
            pattern='[0-9a-fA-F]+',
            examples=['0123456789ABCDEF'],
            type="string",
        )

    def __repr__(self):
        return f'DatabaseID ({super().__repr__()})'


class DecodedDatabaseIdField(int, BaseDatabaseIdField):

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError('String required')
        if v.startswith("F"):
            # Library Folder ids start with an additional "F"
            v = v[1:]
        len_v = len(v)
        if len_v % ENCODED_ID_LENGTH_MULTIPLE:
            raise ValueError('Invalid id length, must be multiple of 16')
        m = ENCODED_DATABASE_ID_PATTERN.fullmatch(v.lower())
        if not m:
            raise ValueError('Invalid characters in encoded ID')
        return cls(cls.security.decode_id(v))


class EncodedDatabaseIdField(str, BaseDatabaseIdField):

    @classmethod
    def validate(cls, v):
        if isinstance(v, int):
            return cls(cls.security.encode_id(v))
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


def ModelClassField(class_name: str) -> str:
    """Represents a database model class name annotated as a constant
    pydantic Field.
    :param class_name: The name of the database class.
    :return: A constant pydantic Field with default annotations for model classes.
    """
    return Field(
        class_name,
        title="Model class",
        description="The name of the database model class.",
        const=True,  # Make this field constant
    )


def OrderParamField(default_order: str) -> Optional[str]:
    return Field(
        default=default_order,
        title="Order",
        description=(
            "String containing one of the valid ordering attributes followed (optionally) "
            "by '-asc' or '-dsc' for ascending and descending order respectively. "
            "Orders can be stacked as a comma-separated list of values."
        ),
        example="name-dsc,create_time",
    )


def optional(*fields):
    """Decorator function used to modify a pydantic model's fields to all be optional.
    Alternatively, you can  also pass the field names that should be made optional as arguments
    to the decorator.
    Taken from https://github.com/samuelcolvin/pydantic/issues/1223#issuecomment-775363074
    """
    def dec(_cls):
        for field in fields:
            _cls.__fields__[field].required = False
        return _cls

    if fields and inspect.isclass(fields[0]) and issubclass(fields[0], BaseModel):
        cls = fields[0]
        fields = cls.__fields__
        return dec(cls)

    return dec
