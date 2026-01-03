import os
import tempfile

import pytest

from galaxy_test.driver import integration_util


def _job_conf(htcondor_params: str) -> str:
    return f"""
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
    workers: 1
  htcondor:
    load: galaxy.jobs.runners.htcondor:HTCondorJobRunner
    workers: 1
execution:
  default: htcondor_environment
  environments:
    htcondor_environment:
      runner: htcondor{htcondor_params}
    local_environment:
      runner: local
tools:
  - id: __DATA_FETCH__
    environment: local_environment
"""


def _htcondor_params():
    lines = []
    collector = os.environ.get("GALAXY_TEST_HTCONDOR_COLLECTOR")
    schedd = os.environ.get("GALAXY_TEST_HTCONDOR_SCHEDD")
    condor_config = os.environ.get("GALAXY_TEST_HTCONDOR_CONFIG")
    request_memory = os.environ.get("GALAXY_TEST_HTCONDOR_REQUEST_MEMORY", "512")
    if collector:
        lines.append(f'      htcondor_collector: "{collector}"')
    if schedd:
        lines.append(f'      htcondor_schedd: "{schedd}"')
    if condor_config:
        lines.append(f'      htcondor_config: "{condor_config}"')
    if request_memory:
        lines.append(f"      request_memory: {request_memory}")
    return ("\n" + "\n".join(lines)) if lines else ""


def _handle_galaxy_config_kwds(config):
    if not os.environ.get("GALAXY_TEST_HTCONDOR"):
        pytest.skip("GALAXY_TEST_HTCONDOR not configured for htcondor integration tests")
    try:
        import htcondor2  # noqa: F401
    except Exception:
        pytest.skip("htcondor2 is not installed in the test environment")

    htcondor_params = _htcondor_params()
    job_conf_str = _job_conf(htcondor_params)
    with tempfile.NamedTemporaryFile(suffix="_htcondor_job_conf.yml", mode="w", delete=False) as job_conf:
        job_conf.write(job_conf_str)
    config["job_config_file"] = job_conf.name
    job_working_directory = os.environ.get("GALAXY_TEST_HTCONDOR_JOB_WORKING_DIRECTORY")
    if not job_working_directory:
        job_working_directory = tempfile.mkdtemp(prefix="htcondor_job_working_", dir=os.getcwd())
    os.makedirs(job_working_directory, exist_ok=True)
    os.chmod(job_working_directory, 0o777)
    config["job_working_directory"] = job_working_directory
    data_directory = os.environ.get("GALAXY_TEST_HTCONDOR_DATA_DIR")
    if not data_directory:
        data_directory = tempfile.mkdtemp(prefix="htcondor_data_", dir=os.getcwd())
    os.chmod(data_directory, 0o777)
    file_path = os.path.join(data_directory, "files")
    new_file_path = os.path.join(data_directory, "new_files")
    os.makedirs(file_path, exist_ok=True)
    os.makedirs(new_file_path, exist_ok=True)
    os.chmod(file_path, 0o777)
    os.chmod(new_file_path, 0o777)
    config["file_path"] = file_path
    config["new_file_path"] = new_file_path


class HTCondorIntegrationInstance(integration_util.IntegrationInstance):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        _handle_galaxy_config_kwds(config)


instance = integration_util.integration_module_instance(HTCondorIntegrationInstance)

test_tools = integration_util.integration_tool_runner(["simple_constructs"])
