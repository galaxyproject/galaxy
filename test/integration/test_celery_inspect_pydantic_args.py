from celery import current_app

from galaxy.celery import galaxy_task
from galaxy.schema.tasks import PurgeDatasetsTaskRequest
from galaxy_test.driver.integration_util import IntegrationTestCase


@galaxy_task
def echo_pydantic_request(request: PurgeDatasetsTaskRequest):
    return request.dataset_ids


class TestCeleryInspectPydanticArgsIntegration(IntegrationTestCase):
    """Worker replies to inspect() commands must be able to encode pydantic task arguments.

    Uses scheduled() rather than active(): the test worker's solo pool cannot answer
    control commands while a task runs. Both replies carry the same Request.info() payload.
    """

    def test_inspect_scheduled_with_pydantic_task_args(self):
        inspect = current_app.control.inspect(timeout=3)
        assert inspect.ping(), "worker does not answer control commands at all"
        request = PurgeDatasetsTaskRequest(dataset_ids=[1, 2])
        result = echo_pydantic_request.apply_async(kwargs={"request": request}, countdown=15)
        scheduled_response = inspect.scheduled()
        assert scheduled_response, "worker did not answer the scheduled() control command"
        scheduled_requests = {
            entry["request"]["id"]: entry["request"] for entries in scheduled_response.values() for entry in entries
        }
        assert result.id in scheduled_requests, f"task {result.id} missing from {scheduled_response}"
        assert scheduled_requests[result.id]["kwargs"]["request"] == request
        assert result.get(timeout=60) == [1, 2]
