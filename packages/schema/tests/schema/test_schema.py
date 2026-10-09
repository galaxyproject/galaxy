import re
from uuid import uuid4

import pytest
from pydantic import (
    BaseModel,
    ValidationError,
)

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.exceptions.utils import validation_error_to_message_exception
from galaxy.schema.schema import (
    DatasetStateField,
    OAuth2State,
    RemoteUserCreationPayload,
    TAG_ITEM_PATTERN,
    UserCreationPayload,
    UserUpdatePayload,
)
from galaxy.schema.tasks import (
    GenerateInvocationDownload,
    RequestUser,
)

TEST_GALAXY_URL = "http://usegalaxy.org"
TEST_USER_ID = 1
TEST_INVOCATION_ID = 5


def test_task_schema():
    user = RequestUser(user_id=TEST_USER_ID)
    download = GenerateInvocationDownload(
        invocation_id=TEST_INVOCATION_ID,
        short_term_storage_request_id=str(uuid4()),
        galaxy_url=TEST_GALAXY_URL,
        user=user,
    )
    rehydrated_download = GenerateInvocationDownload(**download.model_dump())
    assert rehydrated_download.invocation_id == TEST_INVOCATION_ID
    assert rehydrated_download.user.user_id == TEST_USER_ID
    assert rehydrated_download.galaxy_url == TEST_GALAXY_URL


class StateModel(BaseModel):
    state: DatasetStateField


def test_dataset_state_coercion():
    assert StateModel(state="ok").state == "ok"
    assert StateModel(state="deleted").state == "discarded"


class TestTagPattern:
    def test_valid(self):
        tag_strings = [
            "a",
            "aa",
            "aa.aa",
            "aa.aa.aa",
            "~!@#$%^&*()_+`-=[]{};'\",./<>?",
            "a.b:c",
            "a.b:c.d:e.f",
            "a.b:c.d:e..f",
            "a.b:c.d:e.f:g",
            "a.b:c.d:e.f::g",
            "a.b:c.d:e.f::g:h",
            "a::a",  # leading colon for tag value
            "a:.a",  # leading period for tag value
            "a:a:",  # trailing colon OK for tag value
            "a:a.",  # trailing period OK for tag value
        ]
        for t in tag_strings:
            assert re.match(TAG_ITEM_PATTERN, t)

    def test_invalid(self):
        tag_strings = [
            " a",  # leading space for tag name
            ":a",  # leading colon for tag name
            ".a",  # leading period for tag name
            "a ",  # trailing space for tag name
            "a a",  # space inside tag name
            "a: a",  # leading space for tag value
            "a:a a",  # space inside tag value
            "a:",  # trailing colon for tag name
            "a.",  # trailing period for tag name
            "a:b ",  # trailing space for tag value
        ]
        for t in tag_strings:
            assert not re.match(TAG_ITEM_PATTERN, t)


def test_oauth_state():
    state_in = OAuth2State(route="/file_sources/dropbox", nonce="abcde56")
    state_out = OAuth2State.decode(state_in.encode())
    assert state_out.route == "/file_sources/dropbox"
    assert state_out.nonce == "abcde56"


@pytest.mark.parametrize("field", ["active", "email", "username"])
def test_user_update_payload_rejects_null(field):
    with pytest.raises(ValidationError):
        UserUpdatePayload.model_validate({field: None})
    assert "anyOf" not in UserUpdatePayload.model_json_schema()["properties"][field]


def test_user_update_payload_null_clears():
    payload = UserUpdatePayload.model_validate({"display_name": None, "preferred_object_store_id": None})
    assert payload.model_dump(exclude_unset=True) == {"display_name": None, "preferred_object_store_id": None}


@pytest.mark.parametrize(
    "model, field, other_fields",
    [
        (UserUpdatePayload, "email", {}),
        (UserCreationPayload, "email", {"username": "ada", "password": "testpass"}),
        (RemoteUserCreationPayload, "remote_user_email", {}),
    ],
)
def test_user_email_fields(model, field, other_fields):
    payload = model.model_validate({field: "  ada@localhost  ", **other_fields})
    assert getattr(payload, field) == "ada@localhost"

    with pytest.raises(ValidationError) as exc_info:
        model.model_validate({field: "not-an-email", **other_fields})
    exception = validation_error_to_message_exception(exc_info.value)
    assert isinstance(exception, RequestParameterInvalidException)
    assert exception.err_msg == "The format of the email address is not correct."

    with pytest.raises(ValidationError):
        model.model_validate({field: "a" * 250 + "@b.org", **other_fields})


def test_user_username_fields():
    legacy = "Legacy User"
    assert UserUpdatePayload.model_validate({"username": legacy}).username == legacy

    creation = {"email": "ada@localhost", "password": "testpass"}
    assert UserCreationPayload.model_validate({"username": "ada", **creation}).username == "ada"
    with pytest.raises(ValidationError) as exc_info:
        UserCreationPayload.model_validate({"username": legacy, **creation})
    exception = validation_error_to_message_exception(exc_info.value)
    assert isinstance(exception, RequestParameterInvalidException)
    assert exception.err_msg == "Public name must contain only lower-case letters, numbers, '.', '_' and '-'."

    for model, fields in ((UserUpdatePayload, {}), (UserCreationPayload, creation)):
        with pytest.raises(ValidationError):
            model.model_validate({"username": "a" * 256, **fields})
