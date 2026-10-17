"""Run data managers through embedded Pulsar with ``rewrite_parameters: true``."""

import json
import os
import string
from pathlib import Path

from galaxy_test.base.populators import WorkflowPopulator
from .test_tool_data_delete import DataManagerIntegrationTestCase

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
# jobs_directory makes Galaxy compute the remote job layout without creating
# it (LocalSetupHandler), so the staging directories do not exist when the
# job is prepared, as with a Pulsar server on another host.
JOB_CONF_TEMPLATE = string.Template("""
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
    workers: 1
  pulsar:
    load: galaxy.jobs.runners.pulsar:PulsarEmbeddedMQJobRunner
    pulsar_app_config:
      tool_dependency_dir: none
      conda_auto_init: false
      conda_auto_install: false
      message_queue_url: memory://
      staging_directory: ${jobs_directory}
    amqp_url: memory://
execution:
  default: pulsar_mq_environment
  environments:
    pulsar_mq_environment:
      runner: pulsar
      rewrite_parameters: true
      dependency_resolution: none
      default_file_action: remote_transfer
      jobs_directory: ${jobs_directory}
      remote_metadata: true
      outputs_to_working_directory: false
      remote_property_galaxy_home: ${galaxy_home}
${extra_environment_params}
    local_environment:
      runner: local
tools:
  - id: __DATA_FETCH__
    environment: local_environment
""")


class TestDataManagerPulsar(DataManagerIntegrationTestCase):
    temp_tool_data_dir: str
    jobs_directory: Path

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        tool = Path(__file__).resolve().parents[1] / "functional/tools/data_manager_bundle_chain.xml"
        manager_config = Path(cls.temp_tool_data_dir) / "data_managers.xml"
        manager_config.write_text(f"""<data_managers>
  <data_manager id="data_manager_bundle_chain" tool_file="{tool}">
    <data_table name="testbeta">
      <output>
        <column name="value" />
        <column name="path" output_ref="out_file" />
      </output>
    </data_table>
  </data_manager>
</data_managers>""")
        config["data_manager_config_file"] = str(manager_config)
        cls.jobs_directory = Path(cls._test_driver.mkdtemp()).resolve() / "pulsar_staging"
        cls.jobs_directory.mkdir()
        job_conf = Path(cls.temp_tool_data_dir) / "job_conf.yml"
        job_conf.write_text(
            JOB_CONF_TEMPLATE.substitute(
                jobs_directory=cls.jobs_directory,
                galaxy_home=os.path.join(SCRIPT_DIRECTORY, os.pardir),
                extra_environment_params=cls.extra_environment_params(),
            )
        )
        config["job_config_file"] = str(job_conf)
        config["galaxy_infrastructure_url"] = "http://localhost:$GALAXY_WEB_PORT"

    @classmethod
    def extra_environment_params(cls) -> str:
        return ""

    def _assert_ran_on_pulsar(self, job_id: str):
        job = self.dataset_populator.get_job_details(job_id, full=True).json()
        assert job["state"] == "ok", job
        assert job["external_id"]
        destination = self._get(f"jobs/{job_id}/destination_params").json()
        assert destination["Runner"] == "pulsar"
        return job

    def test_populate(self, history_id):
        original_count = self._testbeta_field_count()
        producer = self.dataset_populator.run_tool(
            "data_manager_bundle_chain", {"shape": "dict", "source|kind": "new"}, history_id
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        self._assert_ran_on_pulsar(producer["jobs"][0]["id"])
        assert self._testbeta_field_count() == original_count + 1
        entry = next(field for field in self._testbase_fields() if field[0] == "motus_3.1.0")
        database = Path(entry[1]).resolve()
        assert not database.is_relative_to(self.jobs_directory)
        assert (database / "db_mOTU_versions").read_text() == "3.1.0"

    def test_bundle_chaining(self, history_id):
        populator = self.dataset_populator
        producer = populator.run_tool(
            "data_manager_bundle_chain",
            {"shape": "dict", "source|kind": "new"},
            history_id,
            data_manager_mode="bundle",
        )
        dataset_id = producer["outputs"][0]["id"]
        populator.wait_for_history(history_id, assert_ok=True)
        self._assert_ran_on_pulsar(producer["jobs"][0]["id"])
        version = populator.get_history_dataset_content(
            history_id, dataset_id=dataset_id, filename="db/db_mOTU_versions"
        )
        assert version == "3.1.0"
        index = populator.get_history_dataset_content(
            history_id, dataset_id=dataset_id, filename="_gx_data_bundle_index.json"
        )
        assert json.loads(index)["data_tables"]["testbeta"]["path"] == "db"

        workflows = WorkflowPopulator(self.galaxy_interactor)
        workflow_id = workflows.upload_yaml_workflow(
            {
                "class": "GalaxyWorkflow",
                "inputs": {"bundle": {"type": "data"}},
                "steps": {
                    "consume": {
                        "tool_id": "data_manager_bundle_chain",
                        "tool_state": {"shape": "dict", "source": {"kind": "bundle"}, "__data_manager_mode": "bundle"},
                        "in": {"source|database": "bundle"},
                    },
                },
                "outputs": {"database": {"outputSource": "consume/out_file"}},
            }
        )
        invocation_id = workflows.invoke_workflow_and_assert_ok(
            workflow_id,
            history_id=history_id,
            inputs={"bundle": {"src": "hda", "id": dataset_id}},
            inputs_by="name",
        )
        invocation = workflows.wait_for_invocation_and_completion(invocation_id)
        consumer_job_id = workflows.get_invocation_jobs(invocation_id)[0]["id"]
        consumer_job = self._assert_ran_on_pulsar(consumer_job_id)
        database = Path(consumer_job["command_line"].split("--database ", 1)[1].strip("' "))
        assert database.name == "db"
        assert database.is_relative_to(self.jobs_directory), consumer_job["command_line"]
        version = populator.get_history_dataset_content(
            history_id, dataset_id=invocation["outputs"]["database"]["id"], filename="db/db_mOTU_versions"
        )
        assert version == "3.1.0"


class TestDataManagerPulsarCustomJobWorkingDirectory(TestDataManagerPulsar):
    @classmethod
    def extra_environment_params(cls) -> str:
        return f"      job_working_directory: {cls._test_driver.mkdtemp()}"
