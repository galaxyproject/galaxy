import pytest
from pydantic import (
    BaseModel,
    ValidationError,
)

from galaxy.schema.fields import (
    BaseDatabaseIdField,
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
    LibraryFolderDatabaseIdField,
)
from galaxy.security.idencoding import IdEncodingHelper


class DecodedIdModel(BaseModel):
    id: DecodedDatabaseIdField


class EncodedIdModel(BaseModel):
    id: EncodedDatabaseIdField


class LibraryFolderIdModel(BaseModel):
    id: LibraryFolderDatabaseIdField


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
    encoded_id = security.encode_id(decoded_id)
    model = DecodedIdModel(id=encoded_id)
    assert model.id == decoded_id
    assert DecodedDatabaseIdField.encode(model.id) == encoded_id


def test_library_folder_database_id_field(security: IdEncodingHelper):
    decoded_id = 1
    encoded_id = f"F{security.encode_id(decoded_id)}"
    model = LibraryFolderIdModel(id=encoded_id)
    assert model.id == decoded_id
    assert LibraryFolderDatabaseIdField.encode(model.id) == encoded_id


def test_library_folder_database_id_field_raises_validation_error(security: IdEncodingHelper):
    decoded_id = 1
    # The encoded ID must start with 'F'
    invalid_encoded_id = security.encode_id(decoded_id)
    with pytest.raises(ValidationError):
        LibraryFolderIdModel(id=invalid_encoded_id)
