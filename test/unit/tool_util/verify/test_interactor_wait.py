from unittest import mock

import pytest

from galaxy.tool_util.verify.interactor import GalaxyInteractorApi
from galaxy.tool_util.verify.wait import TimeoutAssertionError


def _interactor(job_state: str) -> GalaxyInteractorApi:
    interactor = GalaxyInteractorApi(galaxy_url="http://localhost:8080", master_api_key=None, api_key="key")
    job_response = mock.Mock()
    job_response.json.return_value = {"state": job_state}
    interactor._get = mock.Mock(return_value=job_response)
    interactor._delete = mock.Mock()
    return interactor


def test_wait_for_job_cancels_job_on_timeout():
    interactor = _interactor("running")
    with pytest.raises(TimeoutAssertionError):
        interactor.wait_for_job("job1", maxseconds=1)
    interactor._delete.assert_called_once_with("jobs/job1")


def test_wait_for_job_timeout_raised_if_cancel_fails():
    interactor = _interactor("running")
    interactor._delete.side_effect = Exception("connection refused")
    with pytest.raises(TimeoutAssertionError):
        interactor.wait_for_job("job1", maxseconds=1)


def test_wait_for_job_does_not_cancel_finished_job():
    interactor = _interactor("ok")
    interactor.wait_for_job("job1", maxseconds=1)
    interactor._delete.assert_not_called()
