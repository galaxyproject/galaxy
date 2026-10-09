"""Verify runtime warnings survive both Galaxy metadata completion paths."""

from pathlib import Path

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class TestRuntimeEnvironmentIntegration(integration_util.IntegrationTestCase):
    jobs_directory: str
    framework_tool_and_types = True
    metadata_strategy = "directory"

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["metadata_strategy"] = cls.metadata_strategy
        config["conda_auto_init"] = False
        config["use_tasked_jobs"] = True
        config["cleanup_job"] = "never"
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config"] = {
            "runners": {"local": {"load": "galaxy.jobs.runners.local:LocalJobRunner"}},
            "execution": {
                "default": "local",
                "environments": {
                    "local": {
                        "runner": "local",
                        "env": [{"name": "LEGACY_VAR", "value": "legacy"}],
                        "job_env": [
                            {"name": "JOB_VAR", "value": "job"},
                            {"execute": "export DECLARED_VAR=declared"},
                            {"name": "EMPTY_VAR", "value": ""},
                        ],
                        "tool_env": [{"name": "TOOL_VAR", "value": "tool"}],
                    }
                },
            },
        }

    def test_scopes_and_required_warning(self):
        populator = DatasetPopulator(self.galaxy_interactor)
        with populator.test_history() as history_id:
            result = populator.run_tool("runtime_environment", {}, history_id)
            populator.wait_for_history(history_id, assert_ok=True)
            content = populator.get_history_dataset_content(history_id)
            assert "LEGACY_VAR=legacy" in content
            assert "JOB_VAR=job" in content
            assert "TOOL_VAR=tool" in content
            assert "DECLARED_VAR=declared" in content
            assert "EMPTY_VAR=\n" in content
            job = populator.get_job_details(result["jobs"][0]["id"], full=True).json()
            warnings = [m for m in job["job_messages"] if m["type"] == "runtime_environment_warning"]
            assert len(warnings) == 1
            assert warnings[0]["variable_names"] == ["MISSING_VAR"]
            assert job["state"] == "ok"

    def test_task_warnings_reach_parent_job(self):
        # Galaxy forces directory metadata for split jobs, even with extended as the instance default.
        populator = DatasetPopulator(self.galaxy_interactor)
        with populator.test_history() as history_id:
            input_dataset = populator.new_dataset(history_id, content="first\nsecond\n", file_type="txt", wait=True)
            result = populator.run_tool(
                "runtime_environment_parallelism", {"input1": {"src": "hda", "id": input_dataset["id"]}}, history_id
            )
            populator.wait_for_history(history_id, assert_ok=True)
            content = populator.get_history_dataset_content(history_id, dataset_id=result["outputs"][0]["id"])
            assert content == "first\nsecond\n"
            job = populator.get_job_details(result["jobs"][0]["id"], full=True).json()
            warnings = [m for m in job["job_messages"] if m["type"] == "runtime_environment_warning"]
            assert len(warnings) == 1
            assert warnings[0]["variable_names"] == ["MISSING_VAR"]
            assert job["state"] == "ok"
            # Verify that the tool actually ran as two tasks, rather than passing as an ordinary job.
            task_warning_files = list(Path(self.jobs_directory).glob("**/task_*/outputs/runtime_environment_warnings"))
            assert len(task_warning_files) == 2


class TestRuntimeEnvironmentExtendedIntegration(TestRuntimeEnvironmentIntegration):
    metadata_strategy = "extended"
