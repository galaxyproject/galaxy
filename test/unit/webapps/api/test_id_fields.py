import pytest
from pydantic import BaseModel

from galaxy.schema.fields import (
    BaseDatabaseIdField,
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)
from galaxy.security.idencoding import IdEncodingHelper


class DecodedIdModel(BaseModel):
    id: DecodedDatabaseIdField


class EncodedIdModel(BaseModel):
    id: EncodedDatabaseIdField


@pytest.fixture
def security() -> IdEncodingHelper:
    BaseDatabaseIdField.security = IdEncodingHelper(id_secret="testing")
    return BaseDatabaseIdField.security


def test_decoded_id_schema_override():
    schema = DecodedIdModel.schema()
    assert schema["properties"]["id"]["type"] == "string", schema


def test_encoded_id_schema_override():
    schema = EncodedIdModel.schema()
    assert schema["properties"]["id"]["type"] == "string", schema


def test_decoded_database_id_field(security: IdEncodingHelper):
    decoded_id = 1
    id_model = EncodedIdModel(id=decoded_id)
    assert id_model.id == security.encode_id(decoded_id)
