import re
import string
import time
from urllib.parse import urljoin
from uuid import uuid4

import requests

from galaxy_test.base.api_asserts import (
    assert_status_code_is,
    assert_status_code_is_ok,
)
from galaxy_test.base.populators import (
    DatasetPopulator,
    wait_on_state,
)
from galaxy_test.driver.integration_util import IntegrationTestCase
from .objectstore._base import BaseObjectStoreIntegrationTestCase
from .objectstore.test_selection_with_resource_parameters import DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE

SIMPLE_DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE = string.Template(
    """<?xml version="1.0"?>
<object_store type="distributed" id="primary" order="0">
    <backends>
        <backend id="default" type="disk" weight="1" name="Default Store">
            <description>This is my description of the default store with *markdown*.</description>
            <files_dir path="${temp_directory}/files_default"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_default"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_default"/>
        </backend>
        <backend id="static" type="disk" weight="0">
            <files_dir path="${temp_directory}/files_static"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_static"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_static"/>
        </backend>
    </backends>
</object_store>
"""
)


class RecalculateDiskUsage:
    task_based: bool
    dataset_populator: DatasetPopulator

    def test_recalculate_user_disk_usage(self):
        # The initial disk usage is 0
        current_usage = self.dataset_populator.get_usage_for(None)
        assert current_usage["total_disk_usage"] == 0
        size = 100
        history_id = self.dataset_populator.new_history()
        hda_id = self.dataset_populator.new_dataset(history_id, content=f"{'0' * size}", wait=True)["id"]
        expected_usage = size + 1  # +1 for the new line character in the dataset
        # The usage should be the total of the datasets
        current_usage = self.dataset_populator.get_usage_for(None)
        assert current_usage["total_disk_usage"] == expected_usage

        self.recalculate_disk_usage()
        # The disk usage should still be the expected usage
        current_usage = self.dataset_populator.get_usage_for(None)
        assert current_usage["total_disk_usage"] == expected_usage

        self.dataset_populator.delete_dataset(history_id, hda_id, purge=True, wait_for_purge=True)

        # Purging that dataset should result in usage dropping back
        # down to zero.
        current_usage = self.dataset_populator.get_usage_for(None)
        assert current_usage["total_disk_usage"] == 0

        self.recalculate_disk_usage()
        # The disk usage should be 0 again
        current_usage = self.dataset_populator.get_usage_for(None)
        assert current_usage["total_disk_usage"] == 0

    def test_purging_output_of_running_job_keeps_other_outputs_counted(self):
        initial_usage = self.dataset_populator.total_disk_usage()
        history_id = self.dataset_populator.new_history()
        # create_2 writes "1\n" to out_file1 and "2\n" to out_file2, then sleeps
        run_response = self.dataset_populator.run_tool("create_2", {"sleep_time": 10}, history_id)
        outputs = {output["output_name"]: output["id"] for output in run_response["outputs"]}
        job_id = run_response["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(job_id, ok_states=["running"])

        # Purge out_file2 while the job runs, before the job charges its outputs
        self.dataset_populator.delete_dataset(history_id, outputs["out_file2"], purge=True, wait_for_purge=True)
        assert self.dataset_populator.get_job_details(job_id).json()["state"] == "running"
        self.dataset_populator.wait_for_job(job_id, assert_ok=True)

        # Only out_file1 is counted, and a recalculation agrees
        expected_usage = initial_usage + 2
        assert self.dataset_populator.total_disk_usage() == expected_usage
        self.recalculate_disk_usage()
        assert self.dataset_populator.total_disk_usage() == expected_usage

        # Purging out_file1 brings the usage back to where it started
        self.dataset_populator.delete_dataset(history_id, outputs["out_file1"], purge=True, wait_for_purge=True)
        assert self.dataset_populator.total_disk_usage() == initial_usage

    def recalculate_disk_usage(self):
        recalculate_response = self.dataset_populator._put("users/current/recalculate_disk_usage")
        if self.task_based:
            task_ok = self.dataset_populator.wait_on_task(recalculate_response)
            assert task_ok
        else:
            time.sleep(2)


class TestRecalculateUserDiskUsageIntegration(IntegrationTestCase, RecalculateDiskUsage):
    framework_tool_and_types = True
    task_based = True
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["allow_user_dataset_purge"] = True

    def test_anonymous_job_finishing_after_login_is_counted(self):
        email = f"user_{uuid4()}@bx.psu.edu"
        password = "testpass"
        self._setup_user(email, password)
        with requests.Session() as session:
            login_page = session.get(urljoin(self.url, "login/start"))
            csrf_token_match = re.search(r'session_csrf_token": "(.*?)"', login_page.text)
            assert csrf_token_match, "session_csrf_token not found on login page"

            # Run create_2 without logging in, it writes "1\n" and "2\n" to its outputs, then sleeps
            history_id = session.get(urljoin(self.url, "history/current_history_json")).json()["id"]
            run_response = session.post(
                urljoin(self.url, "api/tools"),
                json={"tool_id": "create_2", "history_id": history_id, "inputs": {"sleep_time": 10}},
            )
            assert_status_code_is_ok(run_response)
            output_ids = [output["id"] for output in run_response.json()["outputs"]]
            job_url = urljoin(self.url, f"api/jobs/{run_response.json()['jobs'][0]['id']}")
            wait_on_state(lambda: session.get(job_url), desc="job state", ok_states=["running"])

            # Log in while the job runs, which gives the history to the user
            login_response = session.post(
                urljoin(self.url, "user/login"),
                data={"login": email, "password": password, "session_csrf_token": csrf_token_match.group(1)},
            )
            assert_status_code_is(login_response, 200)
            assert session.get(job_url).json()["state"] == "running"

        with self._different_user(email):
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            # The outputs are counted when the job finishes, and a recalculation agrees
            assert self.dataset_populator.total_disk_usage() == 4
            self.recalculate_disk_usage()
            assert self.dataset_populator.total_disk_usage() == 4

            # Purging them brings the usage back to 0
            for output_id in output_ids:
                self.dataset_populator.delete_dataset(history_id, output_id, purge=True, wait_for_purge=True)
            assert self.dataset_populator.total_disk_usage() == 0

    def test_copy_of_running_output_by_another_user_is_counted(self):
        history_id = self.dataset_populator.new_history()
        # create_2 writes "1\n" and "2\n" to its outputs, then sleeps
        run_response = self.dataset_populator.run_tool("create_2", {"sleep_time": 10}, history_id)
        output_id = run_response["outputs"][0]["id"]
        job_id = run_response["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(job_id, ok_states=["running"])
        self.dataset_populator.make_public(history_id)

        with self._different_user(f"user_{uuid4()}@bx.psu.edu"):
            other_history_id = self.dataset_populator.new_history()
            # Copy an output while its job runs, before the job charges it
            copy_response = self.dataset_populator._post(
                f"histories/{other_history_id}/contents",
                {"source": "hda", "content": output_id, "type": "dataset"},
                json=True,
            )
            assert_status_code_is_ok(copy_response)
            self.dataset_populator.wait_for_history(other_history_id, assert_ok=True)

            # The copy is counted when the job finishes, and a recalculation agrees
            assert self.dataset_populator.total_disk_usage() == 2
            self.recalculate_disk_usage()
            assert self.dataset_populator.total_disk_usage() == 2

            # Purging it brings the usage back to 0
            self.dataset_populator.delete_dataset(
                other_history_id, copy_response.json()["id"], purge=True, wait_for_purge=True
            )
            assert self.dataset_populator.total_disk_usage() == 0


class TestFailedJobDiskUsageIntegration(IntegrationTestCase):
    framework_tool_and_types = True
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["allow_user_dataset_purge"] = True
        config.pop("job_config_file", None)
        # Jobs running longer than the walltime are stopped by the runner, which fails them
        config["job_config"] = {
            "runners": {"local": {"load": "galaxy.jobs.runners.local:LocalJobRunner", "workers": 1}},
            "execution": {"default": "local", "environments": {"local": {"runner": "local"}}},
            "limits": [{"type": "walltime", "value": "00:00:05"}],
        }

    def test_failed_job_outputs_are_counted(self):
        initial_usage = self.dataset_populator.total_disk_usage()
        history_id = self.dataset_populator.new_history()
        # create_2 writes "1\n" and "2\n" to its outputs, then sleeps past the walltime
        run_response = self.dataset_populator.run_tool("create_2", {"sleep_time": 60}, history_id)
        output_ids = [output["id"] for output in run_response["outputs"]]
        job_id = run_response["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(job_id, assert_ok=True, ok_states=["error"])

        # The partial outputs of the failed job are counted, and a recalculation agrees
        expected_usage = initial_usage + 4
        assert self.dataset_populator.total_disk_usage() == expected_usage
        recalculate_response = self.dataset_populator._put("users/current/recalculate_disk_usage")
        assert self.dataset_populator.wait_on_task(recalculate_response)
        assert self.dataset_populator.total_disk_usage() == expected_usage

        # Purging them brings the usage back to where it started
        for output_id in output_ids:
            self.dataset_populator.delete_dataset(history_id, output_id, purge=True, wait_for_purge=True)
        assert self.dataset_populator.total_disk_usage() == initial_usage


class TestCopiedRunningOutputDiskUsageIntegration(IntegrationTestCase):
    framework_tool_and_types = True
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["allow_user_dataset_purge"] = True
        # Outputs are moved to the object store when the job finishes, and their size isn't set when importing
        # extended metadata
        config["outputs_to_working_directory"] = True
        config["metadata_strategy"] = "directory"

    def test_copying_output_of_running_job_keeps_its_size(self):
        initial_usage = self.dataset_populator.total_disk_usage()
        history_id = self.dataset_populator.new_history()
        other_history_id = self.dataset_populator.new_history()
        # create_2 writes "1\n" and "2\n" to its outputs, then sleeps
        run_response = self.dataset_populator.run_tool("create_2", {"sleep_time": 10}, history_id)
        output_ids = [output["id"] for output in run_response["outputs"]]
        job_id = run_response["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(job_id, ok_states=["running"])

        # Copy an output while the job runs, before its file is in the object store
        copy_response = self.dataset_populator._post(
            f"histories/{other_history_id}/contents",
            {"source": "hda", "content": output_ids[0], "type": "dataset"},
            json=True,
        )
        assert_status_code_is_ok(copy_response)
        assert self.dataset_populator.get_job_details(job_id).json()["state"] == "running"
        self.dataset_populator.wait_for_job(job_id, assert_ok=True)

        # The copied output gets its full size, it is counted once, and a recalculation agrees
        details = self.dataset_populator.get_history_dataset_details(history_id, dataset_id=output_ids[0])
        assert details["file_size"] == 2
        expected_usage = initial_usage + 4
        assert self.dataset_populator.total_disk_usage() == expected_usage
        recalculate_response = self.dataset_populator._put("users/current/recalculate_disk_usage")
        assert self.dataset_populator.wait_on_task(recalculate_response)
        assert self.dataset_populator.total_disk_usage() == expected_usage

        # Purging the outputs and the copy brings the usage back to where it started
        for output_id in output_ids:
            self.dataset_populator.delete_dataset(history_id, output_id, purge=True, wait_for_purge=True)
        self.dataset_populator.delete_dataset(
            other_history_id, copy_response.json()["id"], purge=True, wait_for_purge=True
        )
        assert self.dataset_populator.total_disk_usage() == initial_usage


class TestRecalculateUserDiskUsageHierarchicalIntegration(BaseObjectStoreIntegrationTestCase, RecalculateDiskUsage):
    task_based = True
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_object_store(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config)
        super().handle_galaxy_config_kwds(config)
        config["allow_user_dataset_purge"] = True


class TestRecalculateUserDiskUsageSimpleHierarchicalIntegration(
    BaseObjectStoreIntegrationTestCase, RecalculateDiskUsage
):
    task_based = True
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_object_store(SIMPLE_DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config)
        super().handle_galaxy_config_kwds(config)
        config["allow_user_dataset_purge"] = True


class TestRecalculateUserDiskUsageHierarchicalNoTaskIntegration(
    BaseObjectStoreIntegrationTestCase, RecalculateDiskUsage
):
    task_based = False
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_object_store(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config)
        super().handle_galaxy_config_kwds(config)
        config["allow_user_dataset_purge"] = True
        config["enable_celery_tasks"] = False
        config["metadata_strategy"] = "extended"
