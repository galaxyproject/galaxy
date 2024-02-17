"""Integration tests for the CLI shell plugins and runners."""

import os
import string
import subprocess
import sys
import tempfile
import time
from typing import (
    ClassVar,
    NamedTuple,
)

import pytest

from galaxy.security.ssh_util import generate_ssh_keys
from galaxy_test.base.populators import skip_without_tool
from galaxy_test.driver import integration_util
from .test_job_environments import BaseJobEnvironmentIntegrationTestCase

PBS_STARTUP_DELAY = 5


class RemoteConnection(NamedTuple):
    hostname: str
    username: str
    port: int
    private_key: str
    public_key: str


def start_ssh_docker(container_name, jobs_directory, port=10022, image="agaveapi/slurm") -> RemoteConnection:
    ssh_keys = generate_ssh_keys()
    START_SLURM_DOCKER = [
        "docker",
        "run",
        "-h",
        "localhost",
        "-p",
        f"{port}:22",
        "-d",
        "--name",
        container_name,
        "--rm",
        "--privileged",  # for torque
        "-v",
        f"{jobs_directory}:{jobs_directory}",
        "-v",
        f"{ssh_keys.public_key_file}:/home/testuser/.ssh/authorized_keys",
        "--ulimit",
        "nofile=2048:2048",
        image,
    ]
    subprocess.check_call(START_SLURM_DOCKER)
    if "openpbs" in image:
        time.sleep(PBS_STARTUP_DELAY)
    if sys.platform != "darwin":
        # Change testuser's uid to match current user id. This ensures that /home/testuser/.ssh/authorized_keys
        # is owned by the right user and that job outputs can be cleaned up.
        subprocess.check_call(["docker", "exec", container_name, "usermod", "-u", str(os.getuid()), "testuser"])
    return RemoteConnection("localhost", "testuser", port, ssh_keys.private_key_file, ssh_keys.public_key_file)


def stop_ssh_docker(container_name, remote_connection):
    subprocess.check_call(["docker", "rm", "-f", container_name])
    os.remove(remote_connection.private_key)
    os.remove(remote_connection.public_key)


def cli_job_config(remote_connection, shell_plugin="ParamikoShell", job_plugin="Slurm"):
    job_conf_template = string.Template(
        """<job_conf>
    <plugins>
        <plugin id="cli" type="runner" load="galaxy.jobs.runners.cli:ShellJobRunner" workers="1"/>
    </plugins>
    <destinations default="shell">
        <destination id="shell" runner="cli">
            <param id="shell_plugin">$shell_plugin</param>
            <param id="job_plugin">$job_plugin</param>
            <param id="shell_username">$username</param>
            <param id="shell_private_key">$private_key</param>
            <param id="shell_hostname">$hostname</param>
            <param id="shell_port">$port</param>
            <param id="shell_strict_host_key_checking">False</param>
            <param id="embed_metadata_in_job">False</param>
            <env id="SOME_ENV_VAR">42</env>
        </destination>
    </destinations>
</job_conf>
"""
    )
    job_conf_str = job_conf_template.substitute(
        shell_plugin=shell_plugin, job_plugin=job_plugin, **remote_connection._asdict()
    )
    with tempfile.NamedTemporaryFile(suffix="_slurm_integration_job_conf.xml", mode="w", delete=False) as job_conf:
        job_conf.write(job_conf_str)
    return job_conf.name


class AbstractTestCases:
    @integration_util.skip_unless_docker()
    class BaseCliIntegrationTestCase(BaseJobEnvironmentIntegrationTestCase):
        container_name: ClassVar[str]
        jobs_directory: ClassVar[str]
        remote_connection: ClassVar[RemoteConnection]
        image: ClassVar[str]
        shell_plugin: ClassVar[str]
        job_plugin: ClassVar[str]

        @classmethod
        def setUpClass(cls):
            cls.container_name = f"{cls.__name__}_container"
            cls.jobs_directory = tempfile.mkdtemp()
            cls.remote_connection = start_ssh_docker(
                container_name=cls.container_name, jobs_directory=cls.jobs_directory, image=cls.image
            )
            super().setUpClass()

        @classmethod
        def tearDownClass(cls):
            stop_ssh_docker(cls.container_name, cls.remote_connection)
            super().tearDownClass()

        @classmethod
        def handle_galaxy_config_kwds(cls, config):
            config["jobs_directory"] = cls.jobs_directory
            config["file_path"] = cls.jobs_directory
            config["job_config_file"] = cli_job_config(
                remote_connection=cls.remote_connection, shell_plugin=cls.shell_plugin, job_plugin=cls.job_plugin
            )

        @skip_without_tool("job_environment_default")
        def test_running_cli_job(self):
            job_env = self._run_and_get_environment_properties()
            assert job_env.some_env == "42"


@pytest.mark.xfail(reason="Container entrypoint occasionally fails to set default queue")
class OpenPBSSetup:
    job_plugin = "OpenPBS"
    image = "mvdbeek/galaxy-integration-docker-images:openpbs-22.01"


class SlurmSetup:
    job_plugin = "Slurm"
    image = "mvdbeek/galaxy-integration-docker-images:slurm-22.01"


class ParamikoShell:
    shell_plugin = "ParamikoShell"


class SecureShell:
    shell_plugin = "SecureShell"


class TestParamikoCliSlurmIntegration(SlurmSetup, ParamikoShell, AbstractTestCases.BaseCliIntegrationTestCase):
    pass


class TestShellJobCliSlurmIntegration(SlurmSetup, SecureShell, AbstractTestCases.BaseCliIntegrationTestCase):
    pass


class TestParamikoCliOpenPBSIntegration(OpenPBSSetup, ParamikoShell, AbstractTestCases.BaseCliIntegrationTestCase):
    pass


class TestShellJobCliOpenPBSIntegration(OpenPBSSetup, SecureShell, AbstractTestCases.BaseCliIntegrationTestCase):
    pass
