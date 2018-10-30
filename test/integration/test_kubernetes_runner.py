"""Integration tests for the CLI shell plugins and runners."""
import collections
import os
import string
import subprocess
import tempfile

from base import integration_util  # noqa: I100,I202
from base.populators import skip_without_tool
from .test_job_environments import BaseJobEnvironmentIntegrationTestCase  # noqa: I201

integration_util.skip_unless_kubernetes()

PERSISTENT_VOLUME_NAME = 'pv-galaxy-integration-test'
PERSISTENT_VOLUME_CLAIM_NAME = 'galaxy-pvc-integration-test'
Config = collections.namedtuple('ConfigTuple', 'path')


class KubeSetupConfigTuple(Config):

    def setup(self):
        subprocess.check_call(['kubectl', 'create', '-f', self.path])

    def teardown(self):
        subprocess.check_call(['kubectl', 'delete', '-f', self.path])


def persistent_volume(path):
    volume_yaml = string.Template("""
kind: PersistentVolume
apiVersion: v1
metadata:
  name: $persistent_volume_name
  labels:
    type: local
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: manual
  local:
    path: $path
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: app
          operator: NotIn
          values:
            - 'i-do-not-exist'
    """).substitute(path=path,
                    persistent_volume_name=PERSISTENT_VOLUME_NAME)
    with tempfile.NamedTemporaryFile(suffix="_persistent_volume.yml", mode="w", delete=False) as volume:
        volume.write(volume_yaml)
    return KubeSetupConfigTuple(path=volume.name)


def persistent_volume_claim():
    peristent_volume_claim_yaml = string.Template("""
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: $persistent_volume_claim_name
spec:
  accessModes:
    - ReadWriteMany
  volumeName: $persistent_volume_name
  resources:
    requests:
      storage: 2Gi
  storageClassName: manual
""").substitute(persistent_volume_name=PERSISTENT_VOLUME_NAME,
                persistent_volume_claim_name=PERSISTENT_VOLUME_CLAIM_NAME)
    with tempfile.NamedTemporaryFile(suffix="_persistent_volume_claim.yml", mode="w", delete=False) as volume_claim:
        volume_claim.write(peristent_volume_claim_yaml)
    return KubeSetupConfigTuple(path=volume_claim.name)


def job_config(path):
    job_conf_template = string.Template("""<job_conf>
    <plugins>
        <plugin id="k8s" type="runner" load="galaxy.jobs.runners.kubernetes:KubernetesJobRunner">
            <param id="k8s_persistent_volume_claim_name">galaxy-pvc-integration-test</param>
            <param id="k8s_persistent_volume_claim_mount_path">$path</param>
            <param id="k8s_config_path">$k8s_config_path</param>
            <param id="k8s_galaxy_instance_id">gx-short-id</param>
        </plugin>
    </plugins>
    <destinations default="k8s_destination">
        <destination id="k8s_destination" runner="k8s">
            <param id="docker_enabled">true</param>
            <env id="SOME_ENV_VAR">42</env>
        </destination>
    </destinations>
</job_conf>
""")
    job_conf_str = job_conf_template.substitute(path=path, k8s_config_path=os.environ.get('GALAXY_TEST_KUBE_CONFIG_PATH', '~/.kube/config'))
    with tempfile.NamedTemporaryFile(suffix="_kubernetes_integration_job_conf", mode="w", delete=False) as job_conf:
        job_conf.write(job_conf_str)
    return Config(job_conf.name)


class BaseKubernetesIntegrationTestCase(BaseJobEnvironmentIntegrationTestCase):

    @classmethod
    def setUpClass(cls):
        cls.jobs_directory = tempfile.mkdtemp()
        cls.persistent_volume = persistent_volume(path=cls.jobs_directory)
        cls.persistent_volume.setup()
        cls.persistent_volume_claim = persistent_volume_claim()
        cls.persistent_volume_claim.setup()
        cls.job_config = job_config(path=cls.jobs_directory)
        super(BaseKubernetesIntegrationTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.persistent_volume_claim.teardown()
        cls.persistent_volume.teardown()
        super(BaseKubernetesIntegrationTestCase, cls).tearDownClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config, ):
        config["jobs_directory"] = cls.jobs_directory
        config["file_path"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config.path

    @skip_without_tool("job_environment_default")
    def test_running_cli_job(self):
        job_env = self._run_and_get_environment_properties()
        assert job_env.some_env == '42'
