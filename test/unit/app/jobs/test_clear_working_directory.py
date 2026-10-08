import os
from unittest.mock import (
    MagicMock,
    Mock,
)

import pytest

from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.jobs import JobWrapper
from galaxy.model import Job


@pytest.mark.parametrize("protection_scheme", [None, "crypt4gh"])
def test_resubmitted_jobs_only_keep_unprotected_working_directories(tmp_path, protection_scheme):
    job = Job()
    job.id = 1
    job.working_directory = str(tmp_path / "jobs")
    job.protection_scheme = protection_scheme
    jwd = JobWorkingDirectory(job, MagicMock())
    working_directory = jwd.create()
    with open(os.path.join(working_directory, "plaintext"), "w") as f:
        f.write("decrypted")
    wrapper = Mock(working_directory=working_directory, object_store=MagicMock(), job_id=job.id)
    wrapper.get_job.return_value = job

    JobWrapper.clear_working_directory(wrapper)

    cleared = [files for _, _, files in os.walk(jwd.cleared_contents_base()) if files]
    assert cleared == ([] if protection_scheme else [["plaintext"]])
    assert not os.path.exists(os.path.join(working_directory, "plaintext"))
    wrapper._setup_working_directory.assert_called_once_with(job=job)
