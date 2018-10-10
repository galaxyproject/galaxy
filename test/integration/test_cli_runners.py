"""Integration tests for the CLI shell plugins and runners."""
import collections
import shlex
import string
import subprocess
import tempfile
import unittest

from base import integration_util
from base.populators import skip_without_tool

from .test_job_environments import BaseJobEnvironmentIntegrationTestCase


def generate_key(key_path):
    CMD = 'ssh-keygen -b 2048 -t rsa -f {key_path} -q -N ""'.format(key_path=key_path)
    subprocess.check_call(shlex.split(CMD))


@integration_util.skip_unless_docker()
def start_ssh_docker(container_name, jobs_directory, port=10022, image='agaveapi/slurm'):
    key_file = tempfile.NamedTemporaryFile(suffix='_slurm_integration_ssh_key', delete=True).name
    generate_key(key_file)
    pub_key = "%s.pub" % key_file
    START_SLURM_DOCKER = ['docker',
                          'run',
                          '-h',
                          'localhost',
                          '-p',
                          '{port}:22'.format(port=port),
                          '-d',
                          '--name',
                          container_name,
                          '--rm',
                          '-v',
                          "{jobs_directory}:{jobs_directory}".format(jobs_directory=jobs_directory),
                          "-v",
                          "{pub_key}:/home/testuser/.ssh/authorized_keys".format(pub_key=pub_key),
                          '--ulimit',
                          'nofile=2048:2048',
                          image]
    subprocess.check_call(START_SLURM_DOCKER)
    return collections.namedtuple('remote_connection', 'hostname username password port private_key')(
        'localhost', 'testuser', 'testuser', port, key_file
    )


def stop_ssh_docker(container_name):
    subprocess.check_call(['docker', 'rm', '-f', container_name])


def cli_job_config(remote_connection, shell_plugin='ParamikoShell', job_plugin='Slurm'):
    job_conf_template = string.Template("""<job_conf>
    <plugins>
        <plugin id="cli" type="runner" load="galaxy.jobs.runners.cli:ShellJobRunner" workers="1"/>
    </plugins>
    <destinations default="ssh_slurm">
        <destination id="ssh_slurm" runner="cli">
            <param id="shell_plugin">$shell_plugin</param>
            <param id="job_plugin">$job_plugin</param>
            <param id="shell_username">$username</param>
            <param id="shell_private_key">$private_key</param>
            <param id="shell_hostname">$hostname</param>
            <param id="shell_port">$port</param>
            <param id="embed_metadata_in_job">False</param>
            <env id="SOME_ENV_VAR">42</env>
        </destination>
    </destinations>
</job_conf>
""")
    job_conf_str = job_conf_template.substitute(shell_plugin=shell_plugin,
                                                job_plugin=job_plugin,
                                                **remote_connection._asdict())
    with tempfile.NamedTemporaryFile(suffix="_slurm_integration_job_conf", delete=False) as job_conf:
        job_conf.write(job_conf_str)
    return job_conf.name


class BaseCliIntegrationTestCase(BaseJobEnvironmentIntegrationTestCase):

    @classmethod
    def setUpClass(cls):
        if cls is BaseCliIntegrationTestCase:
            raise unittest.SkipTest("Base class")
        cls.container_name = "%s_container" % cls.__name__
        cls.jobs_directory = tempfile.mkdtemp()
        cls.remote_connection = start_ssh_docker(container_name=cls.container_name,
                                                 jobs_directory=cls.jobs_directory,
                                                 image=cls.image)
        super(BaseCliIntegrationTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        stop_ssh_docker(container_name=cls.container_name)
        super(BaseCliIntegrationTestCase, cls).tearDownClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config, ):
        config["jobs_directory"] = cls.jobs_directory
        config["file_path"] = cls.jobs_directory
        config["job_config_file"] = cli_job_config(remote_connection=cls.remote_connection,
                                                   shell_plugin=cls.shell_plugin,
                                                   job_plugin=cls.job_plugin)

    @skip_without_tool("job_environment_default")
    def test_running_cli_job(self):
        job_env = self._run_and_get_environment_properties()
        assert job_env.some_env == '42'


class TorqueSetup(object):
    job_plugin = 'Torque'
    image = 'mvdbeek/galaxy-integration-docker-images:torque_latest'


class SlurmSetup(object):
    job_plugin = 'Slurm'
    image = 'mvdbeek/galaxy-integration-docker-images:slurm_latest'


class ParamikoShell(object):
    shell_plugin = 'ParamikoShell'


class SecureShell(object):
    shell_plugin = 'SecureShell'


class ParamikoCliSlurmIntegrationTestCase(SlurmSetup, ParamikoShell, BaseCliIntegrationTestCase):
    pass


class ShellJobCliSlurmIntegrationTestCase(SlurmSetup, SecureShell, BaseCliIntegrationTestCase):
    pass


class ParamikoCliTorqueIntegrationTestCase(TorqueSetup, ParamikoShell, BaseCliIntegrationTestCase):
    pass


class ShellJobCliTorqueIntegrationTestCase(TorqueSetup, SecureShell, BaseCliIntegrationTestCase):
    pass
