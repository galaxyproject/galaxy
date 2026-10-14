from contextlib import contextmanager
from typing import (
    Iterator,
    Tuple,
)
from unittest import mock

import pytest

from galaxy.tool_util.verify.interactor import GalaxyInteractorApi
from galaxy.tool_util.verify.wait import TimeoutAssertionError


@contextmanager
def _interactor(job_state: str) -> Iterator[Tuple[GalaxyInteractorApi, mock.MagicMock]]:
    interactor = GalaxyInteractorApi(galaxy_url="http://localhost:8080", master_api_key=None, api_key="key")
    job_response = mock.Mock()
    job_response.json.return_value = {"state": job_state}
    with mock.patch.object(interactor, "_get", return_value=job_response):
        with mock.patch.object(interactor, "_delete") as delete:
            yield interactor, delete


def test_wait_for_job_cancels_job_on_timeout():
    with _interactor("running") as (interactor, delete):
        with pytest.raises(TimeoutAssertionError):
            interactor.wait_for_job("job1", maxseconds=1)
    delete.assert_called_once_with("jobs/job1")


def test_wait_for_job_timeout_raised_if_cancel_fails():
    with _interactor("running") as (interactor, delete):
        delete.side_effect = Exception("connection refused")
        with pytest.raises(TimeoutAssertionError):
            interactor.wait_for_job("job1", maxseconds=1)


def test_wait_for_job_does_not_cancel_finished_job():
    with _interactor("ok") as (interactor, delete):
        interactor.wait_for_job("job1", maxseconds=1)
    delete.assert_not_called()
