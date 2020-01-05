"""Integration tests for the Kubernetes runner."""
# Tested on docker for mac 18.06.1-ce-mac73 using the default kubernetes setup,
# also works on minikube
import collections
import json
import os
import string
import subprocess
import tempfile
import time

import pytest

from galaxy_test.base.populators import skip_without_tool
from galaxy_test.driver import integration_util
from .test_containerized_jobs import MulledJobTestCases
from .test_job_environments import BaseJobEnvironmentIntegrationTestCase

PERSISTENT_VOLUME_NAME = 'pv-galaxy-integration-test'
PERSISTENT_VOLUME_CLAIM_NAME = 'galaxy-pvc-integration-test'
Config = collections.namedtuple('ConfigTuple', 'path')
TOOL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'tools'))


class KubeSetupConfigTuple(Config):

    def setup(self):
        subprocess.check_call(['kubectl', 'create', '-f', self.path])

    def teardown(self):
        subprocess.check_call(['kubectl', 'delete', '-f', self.path])


def persistent_volume(path, persistent_volume_name):
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
                    persistent_volume_name=persistent_volume_name)
    with tempfile.NamedTemporaryFile(suffix="_persistent_volume.yml", mode="w", delete=False) as volume:
        volume.write(volume_yaml)
    return KubeSetupConfigTuple(path=volume.name)


def persistent_volume_claim(persistent_volume_name, persistent_volum_claim_name):
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
""").substitute(persistent_volume_name=persistent_volume_name,
                persistent_volume_claim_name=persistent_volum_claim_name)
    with tempfile.NamedTemporaryFile(suffix="_persistent_volume_claim.yml", mode="w", delete=False) as volume_claim:
        volume_claim.write(peristent_volume_claim_yaml)
    return KubeSetupConfigTuple(path=volume_claim.name)


def job_config(jobs_directory):
    job_conf_template = string.Template("""<job_conf>
    <plugins>
        <plugin id="local" type="runner" load="galaxy.jobs.runners.local:LocalJobRunner" workers="2"/>
        <plugin id="k8s" type="runner" load="galaxy.jobs.runners.kubernetes:KubernetesJobRunner">
            <param id="k8s_persistent_volume_claims">jobs-directory-claim:$jobs_directory,tool-directory-claim:$tool_directory</param>
            <param id="k8s_config_path">$k8s_config_path</param>
            <param id="k8s_galaxy_instance_id">gx-short-id</param>
            <param id="k8s_run_as_user_id">$$uid</param>
        </plugin>
        <plugin id="k8s_walltime_short" type="runner" load="galaxy.jobs.runners.kubernetes:KubernetesJobRunner">
            <param id="k8s_persistent_volume_claims">jobs-directory-claim:$jobs_directory,tool-directory-claim:$tool_directory</param>
            <param id="k8s_config_path">$k8s_config_path</param>
            <param id="k8s_galaxy_instance_id">gx-short-id</param>
            <param id="k8s_walltime_limit">10</param>
            <param id="k8s_run_as_user_id">$$uid</param>
        </plugin>
        <plugin id="k8s_no_cleanup" type="runner" load="galaxy.jobs.runners.kubernetes:KubernetesJobRunner">
            <param id="k8s_persistent_volume_claims">jobs-directory-claim:$jobs_directory,tool-directory-claim:$tool_directory</param>
            <param id="k8s_config_path">$k8s_config_path</param>
            <param id="k8s_galaxy_instance_id">gx-short-id</param>
            <param id="k8s_cleanup_job">never</param>
            <param id="k8s_run_as_user_id">$$uid</param>
        </plugin>
    </plugins>
    <destinations default="k8s_destination">
        <destination id="k8s_destination" runner="k8s">
            <param id="limits_cpu">1.1</param>
            <param id="limits_memory">10M</param>
            <param id="docker_enabled">true</param>
            <param id="docker_default_container_id">busybox:ubuntu-14.04</param>
            <env id="SOME_ENV_VAR">42</env>
        </destination>
        <destination id="k8s_destination_walltime_short" runner="k8s_walltime_short">
            <param id="limits_cpu">1.1</param>
            <param id="limits_memory">10M</param>
            <param id="docker_enabled">true</param>
            <param id="docker_default_container_id">busybox:ubuntu-14.04</param>
            <env id="SOME_ENV_VAR">42</env>
        </destination>
        <destination id="k8s_destination_no_cleanup" runner="k8s_no_cleanup">
            <param id="limits_cpu">1.1</param>
            <param id="limits_memory">10M</param>
            <param id="docker_enabled">true</param>
            <param id="docker_default_container_id">busybox:ubuntu-14.04</param>
            <env id="SOME_ENV_VAR">42</env>
        </destination>
        <destination id="local_dest" runner="local">
        </destination>
    </destinations>
    <tools>
        <tool id="upload1" destination="local_dest"/>
        <tool id="create_2" destination="k8s_destination_walltime_short"/>
        <tool id="galaxy_slots_and_memory" destination="k8s_destination_no_cleanup"/>
    </tools>
</job_conf>
""")
    job_conf_str = job_conf_template.substitute(jobs_directory=jobs_directory,
                                                tool_directory=TOOL_DIR,
                                                k8s_config_path=integration_util.k8s_config_path(),
                                                )
    with tempfile.NamedTemporaryFile(suffix="_kubernetes_integration_job_conf.xml", mode="w", delete=False) as job_conf:
        job_conf.write(job_conf_str)
    return Config(job_conf.name)


@integration_util.skip_unless_kubernetes()
class BaseKubernetesIntegrationTestCase(BaseJobEnvironmentIntegrationTestCase, MulledJobTestCases):

    def setUp(self):
        super(BaseKubernetesIntegrationTestCase, self).setUp()
        self.history_id = self.dataset_populator.new_history()

    @classmethod
    def setUpClass(cls):
        # realpath for docker deployed in a VM on Mac, also done in driver_util.
        cls.jobs_directory = os.path.realpath(tempfile.mkdtemp())
        cls.volumes = [
            [cls.jobs_directory, 'jobs-directory-volume', 'jobs-directory-claim'],
            [TOOL_DIR, 'tool-directory-volume', 'tool-directory-claim'],
        ]
        cls.persistent_volumes = []
        cls.persistent_volume_claims = []
        for (path, volume, claim) in cls.volumes:
            volume_obj = persistent_volume(path, volume)
            volume_obj.setup()
            cls.persistent_volumes.append(volume_obj)
            claim_obj = persistent_volume_claim(volume, claim)
            claim_obj.setup()
            cls.persistent_volume_claims.append(claim_obj)
        cls.job_config = job_config(jobs_directory=cls.jobs_directory)
        super(BaseKubernetesIntegrationTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        for claim in cls.persistent_volume_claims:
            claim.teardown()
        for volume in cls.persistent_volumes:
            volume.teardown()
        super(BaseKubernetesIntegrationTestCase, cls).tearDownClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        # TODO: implement metadata setting as separate job, as service or side-car
        config['retry_metadata_internally'] = True
        config["jobs_directory"] = cls.jobs_directory
        config["file_path"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config.path
        config["default_job_shell"] = '/bin/sh'
        # Disable tool dependency resolution.
        config["tool_dependency_dir"] = "none"

    @skip_without_tool("job_environment_default")
    def test_job_environment(self):
        job_env = self._run_and_get_environment_properties()
        assert job_env.some_env == '42'

    @skip_without_tool('cat_data_and_sleep')
    def test_kill_process(self):
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
            running_inputs = {
                "input1": {"src": "hda", "id": hda1["id"]},
                "sleep_time": 240,
            }
            running_response = self.dataset_populator.run_tool(
                "cat_data_and_sleep",
                running_inputs,
                history_id,
                assert_ok=False,
            ).json()
            job_dict = running_response["jobs"][0]

            app = self._app
            sa_session = app.model.context.current
            external_id = None
            state = False

            job = sa_session.query(app.model.Job).filter_by(tool_id="cat_data_and_sleep").one()
            # Not checking the state here allows the change from queued to running to overwrite
            # the change from queued to deleted_new in the API thread - this is a problem because
            # the job will still run. See issue https://github.com/galaxyproject/galaxy/issues/4960.
            max_tries = 60
            while max_tries > 0 and external_id is None or state != app.model.Job.states.RUNNING:
                sa_session.refresh(job)
                assert not job.finished
                external_id = job.job_runner_external_id
                state = job.state
                time.sleep(1)
                max_tries -= 1

            status = json.loads(subprocess.check_output(['kubectl', 'get', 'job', external_id, '-o', 'json']))
            assert status['status']['active'] == 1

            delete_response = self.dataset_populator.cancel_job(job_dict["id"])
            assert delete_response.json() is True

            # Wait for job to be cancelled in kubernetes
            time.sleep(2)
            # The default job config removes jobs, didn't find a better way to check that the job doesn't exist anymore
            with pytest.raises(subprocess.CalledProcessError) as excinfo:
                subprocess.check_output(['kubectl', 'get', 'job', external_id, '-o', 'json'], stderr=subprocess.STDOUT)
            assert "not found" in excinfo.value.output.decode()

    @skip_without_tool('job_properties')
    def test_exit_code_127(self):
        inputs = {
            'failbool': True
        }
        running_response = self.dataset_populator.run_tool(
            "job_properties",
            inputs,
            self.history_id,
            assert_ok=False,
        )
        result = self.dataset_populator.wait_for_tool_run(run_response=running_response, history_id=self.history_id, assert_ok=False).json()
        details = self.dataset_populator.get_job_details(result['jobs'][0]['id'], full=True).json()

        assert details['state'] == 'error', details
        assert details['stdout'].strip() == 'The bool is not true', details
        assert details['stderr'].strip() == 'The bool is very not true', details
        assert details['exit_code'] == 127, details

    @skip_without_tool('Count1')
    def test_python_dep(self):
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="1\t2\t3", file_type='tabular', wait=True)
            self.dataset_populator.run_tool(
                'Count1',
                {'input': {"src": "hda", "id": hda1["id"]},
                 'column': [1]},
                self.history_id,
                assert_ok=True,
            )

    @skip_without_tool('galaxy_slots_and_memory')
    def test_slots_and_memory(self):
        running_response = self.dataset_populator.run_tool(
            'galaxy_slots_and_memory',
            {},
            self.history_id,
            assert_ok=True
        )
        dataset_content = self.dataset_populator.get_history_dataset_content(self.history_id, hid=1).strip()
        CPU = '2'
        MEM = '10'
        MEM_PER_SLOT = '5'
        assert [CPU, MEM, MEM_PER_SLOT] == dataset_content.split('\n'), dataset_content

        # Tool is mapped to destination without cleanup, make sure job still exists in kubernetes API
        job_dict = running_response["jobs"][0]
        job = self.galaxy_interactor.get("jobs/%s" % job_dict['id'], admin=True).json()
        external_id = job['external_id']
        status = json.loads(subprocess.check_output(['kubectl', 'get', 'job', external_id, '-o', 'json']))
        assert 'active' not in status['status']

    @skip_without_tool('create_2')
    def test_walltime_limit(self):
        running_response = self.dataset_populator.run_tool(
            'create_2',
            {'sleep_time': 60},
            self.history_id,
            assert_ok=False
        )
        result = self.dataset_populator.wait_for_tool_run(run_response=running_response,
                                                          history_id=self.history_id,
                                                          assert_ok=False).json()
        details = self.dataset_populator.get_job_details(result['jobs'][0]['id'], full=True).json()
        assert details['state'] == 'error'
        hda_details = self.dataset_populator.get_history_dataset_details(self.history_id, assert_ok=False)
        assert hda_details['misc_info'] == 'Job was active longer than specified deadline'
