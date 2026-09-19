import pytest
from pydantic import (
    BaseModel,
    ValidationError,
)

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
    LibraryFolderDatabaseIdField,
    Security,
)


class DecodedIdModel(BaseModel):
    id: DecodedDatabaseIdField


class EncodedIdModel(BaseModel):
    id: EncodedDatabaseIdField


class LibraryFolderIdModel(BaseModel):
    id: LibraryFolderDatabaseIdField


def test_decoded_id_schema_override():
    schema = DecodedIdModel.model_json_schema()
    assert schema["properties"]["id"]["type"] == "string", schema


def test_encoded_id_schema_override():
    schema = EncodedIdModel.model_json_schema()
    assert schema["properties"]["id"]["type"] == "string", schema


def test_decoded_database_id_field():
    decoded_id = 1
    encoded_id = Security.security.encode_id(decoded_id)
    model = DecodedIdModel(id=encoded_id)
    assert model.id == decoded_id
    assert Security.security.encode_id(model.id) == encoded_id


def test_library_folder_database_id_field():
    decoded_id = 1
    encoded_id = f"F{Security.security.encode_id(decoded_id)}"
    model = LibraryFolderIdModel(id=encoded_id)
    assert model.id == decoded_id


def test_library_folder_database_id_field_raises_validation_error():
    decoded_id = 1
    # The encoded ID must start with 'F'
    invalid_encoded_id = Security.security.encode_id(decoded_id)
    with pytest.raises(ValidationError):
        LibraryFolderIdModel(id=invalid_encoded_id)
