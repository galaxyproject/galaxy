from uuid import uuid4

from pydantic import BaseModel

from galaxy.schema.schema import DatasetStateField
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
