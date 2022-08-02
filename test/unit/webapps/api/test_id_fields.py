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


def test_decoded_id_hash(security: IdEncodingHelper):
    id_a = 1
    id_b = 2
    model_a = DecodedIdModel(id=security.encode_id(id_a))
    model_b = DecodedIdModel(id=security.encode_id(id_b))
    model_same_1 = DecodedIdModel(id=security.encode_id(id_a))
    assert hash(model_a.id) != hash(model_b.id)
    assert hash(model_a.id) == hash(model_same_1.id)


def test_encoded_id_hash(security: IdEncodingHelper):
    model_a = EncodedIdModel(id=1)
    model_b = EncodedIdModel(id=2)
    model_same_a = EncodedIdModel(id=1)
    assert hash(model_a.id) != hash(model_b.id)
    assert hash(model_a.id) == hash(model_same_a.id)
