from datetime import timedelta

import pytest

from galaxy.job_execution.protection import (
    ProtectionDestination,
    ProtectionError,
    RecryptorSettings,
)


def _destination(params):
    return ProtectionDestination.from_params(
        params,
        metadata_strategy="extended",
        has_tasks=False,
        is_pulsar=True,
        walltime=timedelta(hours=2),
    )


def test_destination_params_are_read_as_job_configurations_write_them():
    destination = _destination(
        {
            "remote_metadata": "true",
            "rewrite_parameters": "True",
            "live_tool_output_reporting": "false",
            "crypt4gh_recryptor_url": "https://recryptor:61358",
            "crypt4gh_recryptor_timeout": "10",
            "crypt4gh_recryptor_ca_cert": "/etc/ca.pem",
            "crypt4gh_recryptor_verbose_errors": "true",
        }
    )
    assert destination.remote_metadata
    assert destination.rewrite_parameters
    assert not destination.live_tool_output_reporting
    assert destination.walltime == timedelta(hours=2)
    assert destination.recryptor == RecryptorSettings(
        url="https://recryptor:61358", timeout=10, ca_cert="/etc/ca.pem", verbose_errors=True
    )
    destination.check(outputs_in_job_directory=True)


def test_destinations_without_compute_service_are_refused():
    destination = _destination({"remote_metadata": True, "rewrite_parameters": True})
    assert destination.recryptor is None
    with pytest.raises(ProtectionError, match="crypt4gh_recryptor_url"):
        destination.check(outputs_in_job_directory=True)
