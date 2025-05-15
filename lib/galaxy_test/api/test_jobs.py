import datetime
import json
import os
import time
import urllib.parse
from operator import itemgetter
from unittest import SkipTest

import pytest
import requests
from dateutil.parser import isoparse

from galaxy_test.api.test_tools import TestsTools
from galaxy_test.base.api_asserts import assert_status_code_is_ok
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    skip_without_tool,
    wait_on,
    wait_on_state,
    WorkflowPopulator,
)
from ._framework import ApiTestCase


class TestJobsApi(ApiTestCase, TestsTools):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    @pytest.mark.require_new_history
    def test_index(self, history_id):
        # Create HDA to ensure at least one job exists...
        self.__history_with_new_dataset(history_id)
        jobs = self.__jobs_index()
        assert "__DATA_FETCH__" in map(itemgetter("tool_id"), jobs)

    @pytest.mark.require_new_history
    def test_system_details_admin_only(self, history_id):
        self.__history_with_new_dataset(history_id)
        jobs = self.__jobs_index(admin=False)
        job = jobs[0]
        assert job["external_id"] is None

        jobs = self.__jobs_index(admin=True)
        job = jobs[0]
        assert job["command_line"]
        assert job["external_id"]

    @pytest.mark.require_new_history
    def test_admin_job_list(self, history_id):
        self.__history_with_new_dataset(history_id)
        jobs_response = self._get("jobs?view=admin_job_list", admin=False)
        assert jobs_response.status_code == 403
        assert jobs_response.json()["err_msg"] == "Only admins can use the admin_job_list view"

        jobs = self._get("jobs?view=admin_job_list", admin=True).json()
        job = jobs[0]
        self._assert_has_keys(job, "command_line", "external_id", "handler")

    @pytest.mark.require_new_history
    def test_job_list_collection_view(self, history_id):
        self.__history_with_new_dataset(history_id)
        jobs_response = self._get("jobs?view=collection")
        self._assert_status_code_is_ok(jobs_response)
        jobs = jobs_response.json()
        job = jobs[0]
        self._assert_has_keys(job, "id", "tool_id", "state")

    @pytest.mark.require_new_history
    def test_job_list_default_view(self, history_id):
        self.__history_with_new_dataset(history_id)
        jobs_response = self._get(f"jobs?history_id={history_id}")
        self._assert_status_code_is_ok(jobs_response)
        jobs = jobs_response.json()
        job = jobs[0]
        self._assert_has_keys(job, "id", "tool_id", "state")

    @pytest.mark.require_new_history
    def test_index_state_filter(self, history_id):
        # Initial number of ok jobs
        original_count = len(self.__uploads_with_state("ok"))
        # Run through dataset upload to ensure num uplaods at least greater
        # by 1.
        self.__history_with_ok_dataset(history_id)

        # Verify number of ok jobs is actually greater.
        count_increased = False
        for _ in range(10):
            new_count = len(self.__uploads_with_state("ok"))
            if original_count < new_count:
                count_increased = True
                break
            time.sleep(0.1)

        if not count_increased:
            template = "Jobs in ok state did not increase (was %d, now %d)"
            message = template % (original_count, new_count)
            raise AssertionError(message)

    @pytest.mark.require_new_history
    def test_index_date_filter(self, history_id):
        two_weeks_ago = (datetime.datetime.utcnow() - datetime.timedelta(14)).isoformat()
        last_week = (datetime.datetime.utcnow() - datetime.timedelta(7)).isoformat()
        before = datetime.datetime.utcnow().isoformat()
        today = before[:10]
        tomorrow = (datetime.datetime.utcnow() + datetime.timedelta(1)).isoformat()[:10]
        self.__history_with_new_dataset(history_id)
        after = datetime.datetime.utcnow().isoformat()

        # Test using dates
        jobs = self.__jobs_index(data={"date_range_min": today, "date_range_max": tomorrow})
        assert len(jobs) > 0
        today_job = jobs[0]
        today_job_id = today_job["id"]

        # Test using datetimes
        jobs = self.__jobs_index(data={"date_range_min": before, "date_range_max": after})
        assert today_job_id in map(itemgetter("id"), jobs), f"before: {before}, after: {after}, job: {today_job}"

        jobs = self.__jobs_index(data={"date_range_min": two_weeks_ago, "date_range_max": last_week})
        assert today_job_id not in map(itemgetter("id"), jobs)

    @pytest.mark.require_new_history
    def test_index_history(self, history_id):
        self.__history_with_new_dataset(history_id)
        jobs = self.__jobs_index(data={"history_id": history_id})
        assert len(jobs) > 0

        with self.dataset_populator.test_history() as other_history_id:
            jobs = self.__jobs_index(data={"history_id": other_history_id})
            assert len(jobs) == 0

    @pytest.mark.require_new_history
    @skip_without_tool("cat1")
    def test_index_workflow_and_invocation_filter(self, history_id):
        workflow_simple = """
class: GalaxyWorkflow
name: Simple Workflow
inputs:
  input1: data
outputs:
  wf_output_1:
    outputSource: first_cat/out_file1
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: input1
"""
        summary = self.workflow_populator.run_workflow(
            workflow_simple, history_id=history_id, test_data={"input1": "hello world"}
        )
        invocation_id = summary.invocation_id
        workflow_id = self._get(f"invocations/{invocation_id}").json()["workflow_id"]
        self.workflow_populator.wait_for_invocation(workflow_id, invocation_id)
        jobs1 = self.__jobs_index(data={"workflow_id": workflow_id})
        assert len(jobs1) == 1
        jobs2 = self.__jobs_index(data={"invocation_id": invocation_id})
        assert len(jobs2) == 1
        assert jobs1 == jobs2

    @pytest.mark.require_new_history
    @skip_without_tool("multi_data_optional")
    def test_index_workflow_filter_implicit_jobs(self, history_id):
        workflow_id = self.workflow_populator.upload_yaml_workflow(
            """
class: GalaxyWorkflow
inputs:
  input_datasets: collection
steps:
  multi_data_optional:
    tool_id: multi_data_optional
    in:
      input1: input_datasets
"""
        )
        hdca_id = self.dataset_collection_populator.create_list_of_list_in_history(history_id).json()
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        inputs = {
            "0": self.dataset_populator.ds_entry(hdca_id),
        }
        invocation_id = self.workflow_populator.invoke_workflow_and_wait(
            workflow_id, history_id=history_id, inputs=inputs
        ).json()["id"]
        jobs1 = self.__jobs_index(data={"workflow_id": workflow_id})
        jobs2 = self.__jobs_index(data={"invocation_id": invocation_id})
        assert len(jobs1) == len(jobs2) == 1
        second_invocation_id = self.workflow_populator.invoke_workflow_and_wait(
            workflow_id, history_id=history_id, inputs=inputs
        ).json()["id"]
        workflow_jobs = self.__jobs_index(data={"workflow_id": workflow_id})
        second_invocation_jobs = self.__jobs_index(data={"invocation_id": second_invocation_id})
        assert len(workflow_jobs) == 2
        assert len(second_invocation_jobs) == 1

    @pytest.mark.require_new_history
    def test_index_limit_and_offset_filter(self, history_id):
        # create 2 datasets
        self.__history_with_new_dataset(history_id)
        self.__history_with_new_dataset(history_id)
        jobs = self.__jobs_index(data={"history_id": history_id})
        assert len(jobs) > 0
        length = len(jobs)
        jobs = self.__jobs_index(data={"history_id": history_id, "offset": 1})
        assert len(jobs) == length - 1
        jobs = self.__jobs_index(data={"history_id": history_id, "limit": 1})
        assert len(jobs) == 1
        response = self._get("jobs", data={"history_id": history_id, "limit": -1})
        assert response.status_code == 400
        assert response.json()["err_msg"] == "Input should be greater than or equal to 1 in ('query', 'limit')"

    @pytest.mark.require_new_history
    def test_index_search_filter_tool_id(self, history_id):
        self.__history_with_new_dataset(history_id)
        jobs = self.__jobs_index(data={"history_id": history_id})
        assert len(jobs) > 0
        length = len(jobs)
        jobs = self.__jobs_index(data={"history_id": history_id, "search": "emptyresult"})
        assert len(jobs) == 0
        jobs = self.__jobs_index(data={"history_id": history_id, "search": "FETCH"})
        assert len(jobs) == length
        jobs = self.__jobs_index(data={"history_id": history_id, "search": "tool:'FETCH'"})
        assert len(jobs) == 0

    @pytest.mark.require_new_history
    def test_index_search_filter_email(self, history_id):
        self.__history_with_new_dataset(history_id)
        jobs = self.__jobs_index(data={"history_id": history_id, "search": "FETCH"})
        user_email = self.dataset_populator.user_email()
        jobs = self.__jobs_index(data={"history_id": history_id, "search": user_email})
        assert len(jobs) == 0
        # we can search on email...
        jobs = self.__jobs_index(
            data={"history_id": history_id, "search": user_email, "user_details": True}, admin=True
        )
        assert len(jobs) == 1
        # but only if user details are joined in.
        jobs = self.__jobs_index(
            data={"history_id": history_id, "search": user_email, "user_details": False}, admin=True
        )
        assert len(jobs) == 0

    def test_index_user_filter(self):
        test_user_email = "user_for_jobs_index_test@bx.psu.edu"
        user = self._setup_user(test_user_email)
        with self._different_user(email=test_user_email):
            # User should be able to jobs for their own ID.
            jobs = self.__jobs_index(data={"user_id": user["id"]})
            assert jobs == []
        # Admin should be able to see jobs of another user.
        jobs = self.__jobs_index(data={"user_id": user["id"]}, admin=True)
        assert jobs == []
        # Normal user should not be able to see jobs of another user.
        jobs_response = self._get("jobs", data={"user_id": user["id"]})
        self._assert_status_code_is(jobs_response, 403)
        assert jobs_response.json() == {"err_msg": "Only admins can index the jobs of others", "err_code": 403006}

    @pytest.mark.require_new_history
    def test_index_handler_runner_filters(self, history_id):
        self.__history_with_new_dataset(history_id)

        jobs = self._get(f"jobs?view=admin_job_list&history_id={history_id}", admin=True).json()
        job = jobs[0]
        handler = job["handler"]
        assert handler
        runner = job["job_runner_name"]
        assert runner

        # Free text search includes handler and runner for admin list view.
        jobs = self._get(f"jobs?view=admin_job_list&history_id={history_id}&search={handler}", admin=True).json()
        assert jobs
        jobs = self._get(
            f"jobs?view=admin_job_list&history_id={history_id}&search={handler}suffixnotfound", admin=True
        ).json()
        assert not jobs
        jobs = self._get(f"jobs?view=admin_job_list&history_id={history_id}&search={runner}", admin=True).json()
        assert jobs
        jobs = self._get(
            f"jobs?view=admin_job_list&history_id={history_id}&search={runner}suffixnotfound", admin=True
        ).json()
        assert not jobs

        # Test tags for runner and handler specifically.
        assert runner != handler
        jobs = self._get(
            f"jobs?view=admin_job_list&history_id={history_id}&search=handler:%27{handler}%27", admin=True
        ).json()
        assert jobs
        jobs = self._get(
            f"jobs?view=admin_job_list&history_id={history_id}&search=runner:%27{handler}%27", admin=True
        ).json()
        assert not jobs

        jobs = self._get(
            f"jobs?view=admin_job_list&history_id={history_id}&search=runner:%27{runner}%27", admin=True
        ).json()
        assert jobs
        jobs = self._get(
            f"jobs?view=admin_job_list&history_id={history_id}&search=handler:%27{runner}%27", admin=True
        ).json()
        assert not jobs

    @pytest.mark.require_new_history
    def test_index_multiple_states_filter(self, history_id):
        # Initial number of ok jobs
        original_count = len(self.__uploads_with_state("ok", "new"))

        # Run through dataset upload to ensure num uploads at least greater
        # by 1.
        self.__history_with_ok_dataset(history_id)

        # Verify number of ok jobs is actually greater.
        new_count = len(self.__uploads_with_state("new", "ok"))
        assert original_count < new_count, new_count

    @pytest.mark.require_new_history
    def test_show(self, history_id):
        job_properties_tool_run = self.dataset_populator.run_tool(
            tool_id="job_properties",
            inputs={},
            history_id=history_id,
        )
        first_job = self.__jobs_index()[0]
        self._assert_has_key(first_job, "id", "state", "exit_code", "update_time", "create_time")

        job_id = job_properties_tool_run["jobs"][0]["id"]
        show_jobs_response = self.dataset_populator.get_job_details(job_id)
        self._assert_status_code_is(show_jobs_response, 200)

        job_details = show_jobs_response.json()
        self._assert_has_key(job_details, "id", "state", "exit_code", "update_time", "create_time")

        show_jobs_response = self.dataset_populator.get_job_details(job_id, full=True)
        self._assert_status_code_is(show_jobs_response, 200)

        job_details = show_jobs_response.json()
        self._assert_has_key(
            job_details,
            "create_time",
            "exit_code",
            "id",
            "job_messages",
            "job_stderr",
            "job_stdout",
            "state",
            "stderr",
            "stdout",
            "tool_stderr",
            "tool_stdout",
            "update_time",
        )

        self.dataset_populator.wait_for_job(job_id, assert_ok=True)
        show_jobs_response = self.dataset_populator.get_job_details(job_id, full=True)
        job_details = show_jobs_response.json()
        assert "The bool is not true\n" not in job_details["job_stdout"]
        assert "The bool is very not true\n" not in job_details["job_stderr"]
        assert job_details["tool_stdout"] == "The bool is not true\n"
        assert job_details["tool_stderr"] == "The bool is very not true\n"
        assert "The bool is not true\n" in job_details["stdout"]
        assert "The bool is very not true\n" in job_details["stderr"]

    @pytest.mark.require_new_history
    def test_show_security(self, history_id):
        self.__history_with_new_dataset(history_id)
        jobs_response = self._get("jobs", data={"history_id": history_id})
        job = jobs_response.json()[0]
        job_id = job["id"]

        job_lock_response = self._get("job_lock", admin=True)
        job_lock_response.raise_for_status()
        assert not job_lock_response.json()["active"]

        show_jobs_response = self._get(f"jobs/{job_id}", admin=False)
        assert show_jobs_response.json()["external_id"] is None

        # TODO: Re-activate test case when API accepts privacy settings
        # with self._different_user():
        #    show_jobs_response = self._get( "jobs/%s" % job_id, admin=False )
        #    self._assert_status_code_is( show_jobs_response, 200 )

        show_jobs_response = self._get(f"jobs/{job_id}", admin=True)
        assert show_jobs_response.json()["external_id"] is not None
        assert show_jobs_response.json()["command_line"] is not None

    def _run_detect_errors(self, history_id, inputs):
        payload = self.dataset_populator.run_tool_payload(
            tool_id="detect_errors_aggressive",
            inputs=inputs,
            history_id=history_id,
        )
        return self._post("tools", data=payload).json()

    @skip_without_tool("detect_errors_aggressive")
    def test_unhide_on_error(self):
        with self.dataset_populator.test_history() as history_id:
            inputs = {"error_bool": "true"}
            run_response = self._run_detect_errors(history_id=history_id, inputs=inputs)
            job_id = run_response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id)
            job = self.dataset_populator.get_job_details(job_id).json()
            assert job["state"] == "error"
            dataset = self.dataset_populator.get_history_dataset_details(
                history_id=history_id, dataset_id=run_response["outputs"][0]["id"], assert_ok=False
            )
            assert dataset["visible"]

    def _run_map_over_error(self, history_id):
        fetch_response = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=[("sample1-1", "1 2 3")]
        ).json()
        hdca1 = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
        inputs = {
            "error_bool": "true",
            "dataset": {
                "batch": True,
                "values": [{"src": "hdca", "id": hdca1["id"]}],
            },
        }
        return self._run_detect_errors(history_id=history_id, inputs=inputs)

    @skip_without_tool("detect_errors_aggressive")
    def test_no_unhide_on_error_if_mapped_over(self):
        with self.dataset_populator.test_history() as history_id:
            run_response = self._run_map_over_error(history_id)
            job_id = run_response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id)
            job = self.dataset_populator.get_job_details(job_id).json()
            assert job["state"] == "error"
            dataset = self.dataset_populator.get_history_dataset_details(
                history_id=history_id, dataset_id=run_response["outputs"][0]["id"], assert_ok=False
            )
            assert not dataset["visible"]

    def test_no_hide_on_rerun(self):
        with self.dataset_populator.test_history() as history_id:
            run_response = self._run_map_over_error(history_id)
            job_id = run_response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id)
            failed_hdca = self.dataset_populator.get_history_collection_details(
                history_id=history_id,
                content_id=run_response["implicit_collections"][0]["id"],
                assert_ok=False,
            )
            first_update_time = failed_hdca["update_time"]
            assert failed_hdca["visible"]
            rerun_params = self._get(f"jobs/{job_id}/build_for_rerun").json()
            inputs = rerun_params["state_inputs"]
            inputs["rerun_remap_job_id"] = job_id
            rerun_response = self._run_detect_errors(history_id=history_id, inputs=inputs)
            rerun_job_id = rerun_response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(rerun_job_id)
            # Verify source hdca is still visible
            hdca = self.dataset_populator.get_history_collection_details(
                history_id=history_id,
                content_id=run_response["implicit_collections"][0]["id"],
                assert_ok=False,
            )
            assert hdca["visible"]
            assert isoparse(hdca["update_time"]) > (isoparse(first_update_time))

    def test_rerun_exception_handling(self):
        with self.dataset_populator.test_history() as history_id:
            other_run_response = self.dataset_populator.run_tool(
                tool_id="job_properties",
                inputs={},
                history_id=history_id,
            )
            unrelated_job_id = other_run_response["jobs"][0]["id"]
            run_response = self._run_map_over_error(history_id)
            job_id = run_response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id)
            failed_hdca = self.dataset_populator.get_history_collection_details(
                history_id=history_id,
                content_id=run_response["implicit_collections"][0]["id"],
                assert_ok=False,
            )
            assert failed_hdca["visible"]
            rerun_params = self._get(f"jobs/{job_id}/build_for_rerun").json()
            inputs = rerun_params["state_inputs"]
            inputs["rerun_remap_job_id"] = unrelated_job_id
            before_rerun_items = self.dataset_populator.get_history_contents(history_id)
            rerun_response = self._run_detect_errors(history_id=history_id, inputs=inputs)
            assert "does not match rerun tool id" in rerun_response["err_msg"]
            after_rerun_items = self.dataset_populator.get_history_contents(history_id)
            assert len(before_rerun_items) == len(after_rerun_items)

    @skip_without_tool("empty_output")
    def test_common_problems(self):
        with self.dataset_populator.test_history() as history_id:
            empty_run_response = self.dataset_populator.run_tool(
                tool_id="empty_output",
                inputs={},
                history_id=history_id,
            )
            empty_hda = empty_run_response["outputs"][0]
            cat_empty_twice_run_response = self.dataset_populator.run_tool(
                tool_id="cat1",
                inputs={
                    "input1": {"src": "hda", "id": empty_hda["id"]},
                    "queries_0|input2": {"src": "hda", "id": empty_hda["id"]},
                },
                history_id=history_id,
            )
            empty_output_job = empty_run_response["jobs"][0]
            cat_empty_job = cat_empty_twice_run_response["jobs"][0]
            empty_output_common_problems_response = self._get(f"jobs/{empty_output_job['id']}/common_problems").json()
            cat_empty_common_problems_response = self._get(f"jobs/{cat_empty_job['id']}/common_problems").json()
            self._assert_has_keys(empty_output_common_problems_response, "has_empty_inputs", "has_duplicate_inputs")
            self._assert_has_keys(cat_empty_common_problems_response, "has_empty_inputs", "has_duplicate_inputs")
            assert not empty_output_common_problems_response["has_empty_inputs"]
            assert cat_empty_common_problems_response["has_empty_inputs"]
            assert not empty_output_common_problems_response["has_duplicate_inputs"]
            assert cat_empty_common_problems_response["has_duplicate_inputs"]

    @skip_without_tool("detect_errors_aggressive")
    def test_report_error(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_error_report(history_id)

    @skip_without_tool("detect_errors_aggressive")
    def test_report_error_anon(self):
        with self._different_user(anon=True):
            history_id = self._get(urllib.parse.urljoin(self.url, "history/current_history_json")).json()["id"]
            self._run_error_report(history_id)

    def _run_error_report(self, history_id):
        payload = self.dataset_populator.run_tool_payload(
            tool_id="detect_errors_aggressive",
            inputs={"error_bool": "true"},
            history_id=history_id,
        )
        run_response = self._post("tools", data=payload).json()
        job_id = run_response["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(job_id)
        dataset_id = run_response["outputs"][0]["id"]
        response = self._post(f"jobs/{job_id}/error", data={"dataset_id": dataset_id}, json=True)
        assert response.status_code == 200, response.text

    @skip_without_tool("detect_errors_aggressive")
    def test_report_error_bootstrap_admin(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.run_tool_payload(
                tool_id="detect_errors_aggressive",
                inputs={"error_bool": "true"},
                history_id=history_id,
            )
            run_response = self._post("tools", data=payload, key=self.master_api_key)
            self._assert_status_code_is(run_response, 400)

    @pytest.mark.require_new_history
    @skip_without_tool("create_2")
    def test_deleting_output_keep_running_until_all_deleted(self, history_id):
        job_state, outputs = self._setup_running_two_output_job(history_id, 120)

        self._hack_to_skip_test_if_state_ok(job_state)

        # Delete one of the two outputs and make sure the job is still running.
        self._raw_update_history_item(history_id, outputs[0]["id"], {"deleted": True})

        self._hack_to_skip_test_if_state_ok(job_state)

        time.sleep(1)

        self._hack_to_skip_test_if_state_ok(job_state)

        state = job_state().json()["state"]
        assert state == "running", state

        # Delete the second output and make sure the job is cancelled.
        self._raw_update_history_item(history_id, outputs[1]["id"], {"deleted": True})
        final_state = wait_on_state(job_state, assert_ok=False, timeout=15)
        assert final_state in ["deleting", "deleted"], final_state

    @pytest.mark.require_new_history
    @skip_without_tool("create_2")
    def test_purging_output_keep_running_until_all_purged(self, history_id):
        job_state, outputs = self._setup_running_two_output_job(history_id, 120)

        # Pretty much right away after the job is running, these paths should be populated -
        # if they are grab them and make sure they are deleted at the end of the job.
        dataset_1 = self._get_history_item_as_admin(history_id, outputs[0]["id"])
        dataset_2 = self._get_history_item_as_admin(history_id, outputs[1]["id"])
        if "file_name" in dataset_1:
            output_dataset_paths = [dataset_1["file_name"], dataset_2["file_name"]]
            # This may or may not exist depending on if the test is local or not.
            output_dataset_paths_exist = os.path.exists(output_dataset_paths[0])
        else:
            output_dataset_paths = []
            output_dataset_paths_exist = False

        self._hack_to_skip_test_if_state_ok(job_state)

        current_state = job_state().json()["state"]
        assert current_state == "running", current_state

        # Purge one of the two outputs and make sure the job is still running.
        self._raw_update_history_item(history_id, outputs[0]["id"], {"purged": True})
        time.sleep(1)

        self._hack_to_skip_test_if_state_ok(job_state)

        current_state = job_state().json()["state"]
        assert current_state == "running", current_state

        # Purge the second output and make sure the job is cancelled.
        self._raw_update_history_item(history_id, outputs[1]["id"], {"purged": True})
        final_state = wait_on_state(job_state, assert_ok=False, timeout=15)
        assert final_state in ["deleting", "deleted"], final_state

        def paths_deleted():
            if not os.path.exists(output_dataset_paths[0]) and not os.path.exists(output_dataset_paths[1]):
                return True

        if output_dataset_paths_exist:
            wait_on(paths_deleted, "path deletion")

    def test_submission_on_collection_with_deleted_element(self, history_id):
        hdca = self.dataset_collection_populator.create_list_of_list_in_history(history_id=history_id, wait=True).json()
        hda_id = hdca["elements"][0]["object"]["elements"][0]["object"]["id"]
        self.dataset_populator.delete_dataset(history_id=history_id, content_id=hda_id)
        response = self.dataset_populator.run_tool_raw(
            "is_of_type",
            inputs={
                "collection": {"batch": True, "values": [{"src": "hdca", "id": hdca["id"], "map_over_type": "list"}]},
            },
            history_id=history_id,
        )
        assert response.status_code == 400
        assert (
            response.json()["err_msg"]
            == "Parameter 'collection': the previously selected dataset collection has elements that are deleted."
        )

    @pytest.mark.require_new_history
    @skip_without_tool("create_2")
    def test_purging_output_cleaned_after_ok_run(self, history_id):
        job_state, outputs = self._setup_running_two_output_job(history_id, 10)

        # Pretty much right away after the job is running, these paths should be populated -
        # if they are grab them and make sure they are deleted at the end of the job.
        dataset_1 = self._get_history_item_as_admin(history_id, outputs[0]["id"])
        dataset_2 = self._get_history_item_as_admin(history_id, outputs[1]["id"])
        if "file_name" in dataset_1:
            output_dataset_paths = [dataset_1["file_name"], dataset_2["file_name"]]
            # This may or may not exist depending on if the test is local or not.
            output_dataset_paths_exist = os.path.exists(output_dataset_paths[0])
        else:
            output_dataset_paths = []
            output_dataset_paths_exist = False

        if not output_dataset_paths_exist:
            # Given this Galaxy configuration - there is nothing more to be tested here.
            # Consider throwing a skip instead.
            return

        # Purge one of the two outputs and wait for the job to complete.
        self._raw_update_history_item(history_id, outputs[0]["id"], {"purged": True})
        wait_on_state(job_state, assert_ok=True)

        if output_dataset_paths_exist:
            time.sleep(0.5)
            # Make sure the non-purged dataset is on disk and the purged one is not.
            assert os.path.exists(output_dataset_paths[1])
            assert not os.path.exists(output_dataset_paths[0])

    def _hack_to_skip_test_if_state_ok(self, job_state):
        if job_state().json()["state"] == "ok":
            message = "Job state switch from running to ok too quickly - the rest of the test requires the job to be in a running state. Skipping test."
            raise SkipTest(message)

    def _setup_running_two_output_job(self, history_id, sleep_time):
        payload = self.dataset_populator.run_tool_payload(
            tool_id="create_2",
            inputs=dict(
                sleep_time=sleep_time,
            ),
            history_id=history_id,
        )
        run_response = self._post("tools", data=payload)
        run_response.raise_for_status()
        run_object = run_response.json()
        outputs = run_object["outputs"]
        jobs = run_object["jobs"]

        assert len(outputs) == 2
        assert len(jobs) == 1

        def job_state():
            jobs_response = self._get(f"jobs/{jobs[0]['id']}")
            return jobs_response

        # Give job some time to get up and running.
        time.sleep(2)
        running_state = wait_on_state(job_state, skip_states=["queued", "new"], assert_ok=False, timeout=15)
        assert running_state == "running", running_state

        return job_state, outputs

    def _raw_update_history_item(self, history_id, item_id, data):
        update_url = self._api_url(f"histories/{history_id}/contents/{item_id}", use_key=True)
        update_response = requests.put(update_url, json=data)
        assert_status_code_is_ok(update_response)
        return update_response

    @pytest.mark.require_new_history
    @skip_without_tool("cat_data_and_sleep")
    def test_resume_job(self, history_id):
        hda1 = self.dataset_populator.new_dataset(history_id, content="samp1\t10.0\nsamp2\t20.0\n")
        hda2 = self.dataset_populator.new_dataset(history_id, content="samp1\t30.0\nsamp2\t40.0\n")
        # Submit first job
        payload = self.dataset_populator.run_tool_payload(
            tool_id="cat_data_and_sleep",
            inputs={
                "sleep_time": 15,
                "input1": {"src": "hda", "id": hda2["id"]},
                "queries_0|input2": {"src": "hda", "id": hda2["id"]},
            },
            history_id=history_id,
        )
        run_response = self._post("tools", data=payload).json()
        output = run_response["outputs"][0]
        # Submit second job that waits on job1
        payload = self.dataset_populator.run_tool_payload(
            tool_id="cat1",
            inputs={"input1": {"src": "hda", "id": hda1["id"]}, "queries_0|input2": {"src": "hda", "id": output["id"]}},
            history_id=history_id,
        )
        run_response = self._post("tools", data=payload).json()
        job_id = run_response["jobs"][0]["id"]
        output = run_response["outputs"][0]
        # Delete second jobs input while second job is waiting for first job
        delete_response = self._delete(f"histories/{history_id}/contents/{hda1['id']}")
        self._assert_status_code_is(delete_response, 200)
        self.dataset_populator.wait_for_history_jobs(history_id, assert_ok=False)
        dataset_details = self._get(f"histories/{history_id}/contents/{output['id']}").json()
        assert dataset_details["state"] == "paused"
        # Undelete input dataset
        undelete_response = self._put(
            f"histories/{history_id}/contents/{hda1['id']}", data={"deleted": False}, json=True
        )
        self._assert_status_code_is(undelete_response, 200)
        resume_response = self._put(f"jobs/{job_id}/resume")
        self._assert_status_code_is(resume_response, 200)
        self.dataset_populator.wait_for_history_jobs(history_id, assert_ok=True)
        dataset_details = self._get(f"histories/{history_id}/contents/{output['id']}").json()
        assert dataset_details["state"] == "ok"

    def _get_history_item_as_admin(self, history_id, item_id):
        response = self._get(f"histories/{history_id}/contents/{item_id}?view=detailed", admin=True)
        assert_status_code_is_ok(response)
        return response.json()

    @pytest.mark.require_new_history
    def test_search(self, history_id):
        dataset_id = self.__history_with_ok_dataset(history_id)
        # We first copy the datasets, so that the update time is lower than the job creation time
        new_history_id = self.dataset_populator.new_history()
        copy_payload = {"content": dataset_id, "source": "hda", "type": "dataset"}
        copy_response = self._post(f"histories/{new_history_id}/contents", data=copy_payload, json=True)
        self._assert_status_code_is(copy_response, 200)
        inputs = json.dumps({"input1": {"src": "hda", "id": dataset_id}})
        self._job_search(tool_id="cat1", history_id=history_id, inputs=inputs)
        # We test that a job can be found even if the dataset has been copied to another history
        new_dataset_id = copy_response.json()["id"]
        copied_inputs = json.dumps({"input1": {"src": "hda", "id": new_dataset_id}})
        search_payload = self._search_payload(history_id=history_id, tool_id="cat1", inputs=copied_inputs)
        self._search(search_payload, expected_search_count=1)
        # Now we delete the original input HDA that was used -- we should still be able to find the job
        delete_respone = self._delete(f"histories/{history_id}/contents/{dataset_id}")
        self._assert_status_code_is(delete_respone, 200)
        self._search(search_payload, expected_search_count=1)
        # Now we also delete the copy -- we shouldn't find a job
        delete_respone = self._delete(f"histories/{new_history_id}/contents/{new_dataset_id}")
        self._assert_status_code_is(delete_respone, 200)
        self._search(search_payload, expected_search_count=0)

    @pytest.mark.require_new_history
    def test_search_handle_identifiers(self, history_id):
        # Test that input name and element identifier of a jobs' output must match for a job to be returned.
        dataset_id = self.__history_with_ok_dataset(history_id)
        inputs = json.dumps({"input1": {"src": "hda", "id": dataset_id}})
        self._job_search(tool_id="identifier_single", history_id=history_id, inputs=inputs)
        dataset_details = self._get(f"histories/{history_id}/contents/{dataset_id}").json()
        dataset_details["name"] = "Renamed Test Dataset"
        dataset_update_response = self._put(
            f"histories/{history_id}/contents/{dataset_id}", data=dict(name="Renamed Test Dataset"), json=True
        )
        self._assert_status_code_is(dataset_update_response, 200)
        assert dataset_update_response.json()["name"] == "Renamed Test Dataset"
        search_payload = self._search_payload(history_id=history_id, tool_id="identifier_single", inputs=inputs)
        self._search(search_payload, expected_search_count=0)

    @pytest.mark.require_new_history
    def test_search_delete_outputs(self, history_id):
        dataset_id = self.__history_with_ok_dataset(history_id)
        inputs = json.dumps({"input1": {"src": "hda", "id": dataset_id}})
        tool_response = self._job_search(tool_id="cat1", history_id=history_id, inputs=inputs)
        output_id = tool_response.json()["outputs"][0]["id"]
        delete_respone = self._delete(f"histories/{history_id}/contents/{output_id}")
        self._assert_status_code_is(delete_respone, 200)
        search_payload = self._search_payload(history_id=history_id, tool_id="cat1", inputs=inputs)
        self._search(search_payload, expected_search_count=0)

    def test_implicit_collection_jobs(self, history_id):
        run_response = self._run_map_over_error(history_id)
        implicit_collection_id = run_response["implicit_collections"][0]["id"]
        failed_hdca = self.dataset_populator.get_history_collection_details(
            history_id=history_id,
            content_id=implicit_collection_id,
            assert_ok=False,
        )
        job_id = run_response["jobs"][0]["id"]
        icj_id = failed_hdca["implicit_collection_jobs_id"]
        assert icj_id
        index = self.__jobs_index(data=dict(implicit_collection_jobs_id=icj_id))
        assert len(index) == 1
        assert index[0]["id"] == job_id
        assert index[0]["state"] == "error", index

    @pytest.mark.require_new_history
    def test_search_with_hdca_list_input(self, history_id):
        list_id_a = self.__history_with_ok_collection(collection_type="list", history_id=history_id)
        list_id_b = self.__history_with_ok_collection(collection_type="list", history_id=history_id)
        inputs = json.dumps(
            {
                "f1": {"src": "hdca", "id": list_id_a},
                "f2": {"src": "hdca", "id": list_id_b},
            }
        )
        tool_response = self._job_search(tool_id="multi_data_param", history_id=history_id, inputs=inputs)
        # We switch the inputs, this should not return a match
        inputs_switched = json.dumps(
            {
                "f2": {"src": "hdca", "id": list_id_a},
                "f1": {"src": "hdca", "id": list_id_b},
            }
        )
        search_payload = self._search_payload(history_id=history_id, tool_id="multi_data_param", inputs=inputs_switched)
        self._search(search_payload, expected_search_count=0)
        # We delete the ouput (this is a HDA, as multi_data_param reduces collections)
        # and use the correct input job definition, the job should not be found
        output_id = tool_response.json()["outputs"][0]["id"]
        delete_respone = self._delete(f"histories/{history_id}/contents/{output_id}")
        self._assert_status_code_is(delete_respone, 200)
        search_payload = self._search_payload(history_id=history_id, tool_id="multi_data_param", inputs=inputs)
        self._search(search_payload, expected_search_count=0)

    @pytest.mark.require_new_history
    def test_search_delete_hdca_output(self, history_id):
        list_id_a = self.__history_with_ok_collection(collection_type="list", history_id=history_id)
        inputs = json.dumps(
            {
                "input1": {"src": "hdca", "id": list_id_a},
            }
        )
        tool_response = self._job_search(tool_id="collection_creates_list", history_id=history_id, inputs=inputs)
        output_id = tool_response.json()["outputs"][0]["id"]
        # We delete a single tool output, no job should be returned
        delete_respone = self._delete(f"histories/{history_id}/contents/{output_id}")
        self._assert_status_code_is(delete_respone, 200)
        search_payload = self._search_payload(history_id=history_id, tool_id="collection_creates_list", inputs=inputs)
        self._search(search_payload, expected_search_count=0)
        tool_response = self._job_search(tool_id="collection_creates_list", history_id=history_id, inputs=inputs)
        output_collection_id = tool_response.json()["output_collections"][0]["id"]
        # We delete a collection output, no job should be returned
        delete_respone = self._delete(f"histories/{history_id}/contents/dataset_collections/{output_collection_id}")
        self._assert_status_code_is(delete_respone, 200)
        search_payload = self._search_payload(history_id=history_id, tool_id="collection_creates_list", inputs=inputs)
        self._search(search_payload, expected_search_count=0)

    @pytest.mark.require_new_history
    def test_search_with_hdca_pair_input(self, history_id):
        list_id_a = self.__history_with_ok_collection(collection_type="pair", history_id=history_id)
        inputs = json.dumps(
            {
                "f1": {"src": "hdca", "id": list_id_a},
                "f2": {"src": "hdca", "id": list_id_a},
            }
        )
        self._job_search(tool_id="multi_data_param", history_id=history_id, inputs=inputs)
        # We test that a job can be found even if the collection has been copied to another history
        new_history_id = self.dataset_populator.new_history()
        copy_payload = {"content": list_id_a, "source": "hdca", "type": "dataset_collection"}
        copy_response = self._post(f"histories/{new_history_id}/contents", data=copy_payload, json=True)
        self._assert_status_code_is(copy_response, 200)
        new_list_a = copy_response.json()["id"]
        copied_inputs = json.dumps(
            {
                "f1": {"src": "hdca", "id": new_list_a},
                "f2": {"src": "hdca", "id": new_list_a},
            }
        )
        search_payload = self._search_payload(
            history_id=new_history_id, tool_id="multi_data_param", inputs=copied_inputs
        )
        self._search(search_payload, expected_search_count=1)
        # Now we delete the original input HDCA that was used -- we should still be able to find the job
        delete_respone = self._delete(f"histories/{history_id}/contents/dataset_collections/{list_id_a}")
        self._assert_status_code_is(delete_respone, 200)
        self._search(search_payload, expected_search_count=1)
        # Now we also delete the copy -- we shouldn't find a job
        delete_respone = self._delete(f"histories/{history_id}/contents/dataset_collections/{new_list_a}")
        self._assert_status_code_is(delete_respone, 200)
        self._search(search_payload, expected_search_count=0)

    @pytest.mark.require_new_history
    def test_search_with_hdca_list_pair_input(self, history_id):
        list_id_a = self.__history_with_ok_collection(collection_type="list:pair", history_id=history_id)
        inputs = json.dumps(
            {
                "f1": {"src": "hdca", "id": list_id_a},
                "f2": {"src": "hdca", "id": list_id_a},
            }
        )
        self._job_search(tool_id="multi_data_param", history_id=history_id, inputs=inputs)

    @pytest.mark.require_new_history
    def test_search_with_hdca_list_pair_collection_mapped_over_pair_input(self, history_id):
        list_id_a = self.__history_with_ok_collection(collection_type="list:pair", history_id=history_id)
        inputs = json.dumps(
            {
                "f1": {"batch": True, "values": [{"src": "hdca", "id": list_id_a, "map_over_type": "paired"}]},
            }
        )
        self._job_search(tool_id="collection_paired_test", history_id=history_id, inputs=inputs)

    def _get_simple_rerun_params(self, history_id, private=False):
        list_id_a = self.__history_with_ok_collection(collection_type="list:pair", history_id=history_id)
        inputs = {"f1": {"batch": True, "values": [{"src": "hdca", "id": list_id_a, "map_over_type": "paired"}]}}
        run_response = self._run(
            history_id=history_id,
            tool_id="collection_paired_test",
            inputs=inputs,
            wait_for_job=True,
            assert_ok=True,
        )
        rerun_params = self._get(f"jobs/{run_response['jobs'][0]['id']}/build_for_rerun").json()
        # Since we call rerun on the first (and only) job we should get the expanded input
        # which is a dataset collection element (and not the list:pair hdca that was used as input to the original
        # job).
        assert rerun_params["state_inputs"]["f1"]["values"][0]["src"] == "dce"
        if private:
            hdca = self.dataset_populator.get_history_collection_details(history_id=history_id, content_id=list_id_a)
            for element in hdca["elements"][0]["object"]["elements"]:
                self.dataset_populator.make_private(history_id, element["object"]["id"])
        return rerun_params

    @skip_without_tool("collection_paired_test")
    def test_job_build_for_rerun(self, history_id):
        rerun_params = self._get_simple_rerun_params(history_id)
        self._run(
            history_id=history_id,
            tool_id="collection_paired_test",
            inputs=rerun_params["state_inputs"],
            wait_for_job=True,
            assert_ok=True,
        )

    @skip_without_tool("collection_paired_test")
    def test_dce_submission_security(self, history_id):
        rerun_params = self._get_simple_rerun_params(history_id, private=True)
        with self._different_user():
            other_history_id = self.dataset_populator.new_history()
            response = self._run(
                history_id=other_history_id,
                tool_id="collection_paired_test",
                inputs=rerun_params["state_inputs"],
                wait_for_job=False,
                assert_ok=False,
            )
            assert response.status_code == 403

    @skip_without_tool("identifier_collection")
    def test_job_build_for_rerun_list_list(self, history_id):
        list_id_a = self.__history_with_ok_collection(collection_type="list", history_id=history_id)
        list_id_b = self.__history_with_ok_collection(collection_type="list", history_id=history_id)
        list_list = self.dataset_collection_populator.create_nested_collection(
            history_id=history_id,
            collection_type="list:list",
            name="list list collection",
            collection=[list_id_a, list_id_b],
        ).json()
        list_list_id = list_list["id"]
        first_element = list_list["elements"][0]
        assert first_element["element_type"] == "dataset_collection"
        assert first_element["element_identifier"] == "test0"
        assert first_element["model_class"] == "DatasetCollectionElement"
        inputs = {"input1": {"batch": True, "values": [{"src": "hdca", "id": list_list_id, "map_over_type": "list"}]}}
        run_response = self._run(
            history_id=history_id,
            tool_id="identifier_collection",
            inputs=inputs,
            wait_for_job=True,
            assert_ok=True,
        )
        assert len(run_response["jobs"]) == 2
        rerun_params = self._get(f"jobs/{run_response['jobs'][0]['id']}/build_for_rerun").json()
        # Since we call rerun on the first (and only) job we should get the expanded input
        # which is a dataset collection element (and not the list:list hdca that was used as input to the original
        # job).
        assert rerun_params["state_inputs"]["input1"]["values"][0]["src"] == "dce"
        rerun_response = self._run(
            history_id=history_id,
            tool_id="identifier_collection",
            inputs=rerun_params["state_inputs"],
            wait_for_job=True,
            assert_ok=True,
        )
        assert len(rerun_response["jobs"]) == 1
        rerun_content = self.dataset_populator.get_history_dataset_content(
            history_id=history_id, dataset=rerun_response["outputs"][0]
        )
        run_content = self.dataset_populator.get_history_dataset_content(
            history_id=history_id, dataset=run_response["outputs"][0]
        )
        assert rerun_content == run_content

    @pytest.mark.require_new_history
    def test_get_inputs_and_outputs(self, history_id):
        dataset_id = self.__history_with_ok_dataset(history_id)
        inputs = json.dumps({"input1": {"src": "hda", "id": dataset_id}})
        search_response = self._create_and_search_job(history_id, inputs, tool_id="cat1")
        job_id = search_response.json()[0]["id"]
        job_first_output_name, job_first_output_values = list(search_response.json()[0]["outputs"].items())[0]
        # get the inputs of the job
        job_response = self._get(f"jobs/{job_id}/inputs")
        self._assert_status_code_is(job_response, 200)
        job_first_input = job_response.json()[0]
        # validate input response
        assert job_first_input.get("name") == "input1"
        assert job_first_input.get("dataset") == {"src": "hda", "id": dataset_id}
        # get the outputs of the job
        job_response = self._get(f"jobs/{job_id}/outputs")
        self._assert_status_code_is(job_response, 200)
        job_first_output = job_response.json()[0]
        # validate output response
        assert job_first_output.get("name") == job_first_output_name
        assert job_first_output.get("dataset").get("id") == job_first_output_values.get("id")
        assert job_first_output.get("dataset").get("src") == job_first_output_values.get("src")

    @pytest.mark.require_new_history
    def test_delete_job(self, history_id):
        dataset_id = self.__history_with_ok_dataset(history_id)
        inputs = json.dumps({"input1": {"src": "hda", "id": dataset_id}})
        search_payload = self._search_payload(history_id=history_id, tool_id="cat1", inputs=inputs)
        # create a job
        tool_response = self._post("tools", data=search_payload)
        job_id = tool_response.json()["jobs"][0]["id"]
        # delete the job without message
        delete_job_response = self._delete(f"jobs/{job_id}")
        self._assert_status_code_is(delete_job_response, 200)
        assert delete_job_response.json() is True
        # now that we deleted the job we should not find it anymore
        search_payload = self._search_payload(history_id=history_id, tool_id="cat1", inputs=inputs)
        empty_search_response = self._post("jobs/search", data=search_payload, json=True)
        self._assert_status_code_is(empty_search_response, 200)
        assert len(empty_search_response.json()) == 0

    @pytest.mark.require_new_history
    def test_delete_job_with_message(self, history_id):
        input_dataset_id = self.__history_with_ok_dataset(history_id)
        inputs = json.dumps({"input1": {"src": "hda", "id": input_dataset_id}})
        search_payload = self._search_payload(history_id=history_id, tool_id="cat1", inputs=inputs)
        # create a job
        tool_response = self._post("tools", data=search_payload).json()
        job_id = tool_response["jobs"][0]["id"]
        output_dataset_id = tool_response["outputs"][0]["id"]
        # delete the job with message
        expected_message = "test message"
        delete_job_response = self._delete(f"jobs/{job_id}", data={"message": expected_message}, json=True)
        self._assert_status_code_is(delete_job_response, 200)
        # Check the output dataset is deleted and the info field contains the message
        dataset_details = self._get(f"histories/{history_id}/contents/{output_dataset_id}").json()
        assert dataset_details["deleted"] is True
        assert dataset_details["misc_info"] == expected_message

    @pytest.mark.require_new_history
    def test_destination_params(self, history_id):
        dataset_id = self.__history_with_ok_dataset(history_id)
        inputs = json.dumps({"input1": {"src": "hda", "id": dataset_id}})
        search_response = self._create_and_search_job(history_id, inputs, tool_id="cat1")
        job_id = search_response.json()[0]["id"]
        destination_params_response = self._get(f"/api/jobs/{job_id}/destination_params", admin=True)
        self._assert_status_code_is(destination_params_response, 200)

    @pytest.mark.require_new_history
    def test_job_metrics(self, history_id):
        dataset_id = self.__history_with_ok_dataset(history_id)
        inputs = json.dumps({"input1": {"src": "hda", "id": dataset_id}})
        search_response = self._create_and_search_job(history_id, inputs, tool_id="cat1")
        job_id = search_response.json()[0]["id"]
        metrics_by_job_response = self._get(f"/api/jobs/{job_id}/metrics", data={"hda_ldda": "hda"})
        self._assert_status_code_is(metrics_by_job_response, 200)
        metrics_by_dataset_response = self._get(f"/api/datasets/{dataset_id}/metrics", data={"hda_ldda": "hda"})
        self._assert_status_code_is(metrics_by_dataset_response, 200)

    @pytest.mark.require_new_history
    def test_parameters_display(self, history_id):
        dataset_id = self.__history_with_ok_dataset(history_id)
        inputs = json.dumps({"input1": {"src": "hda", "id": dataset_id}})
        search_response = self._create_and_search_job(history_id, inputs, tool_id="cat1")
        job_id = search_response.json()[0]["id"]
        display_parameters_by_job_response = self._get(
            f"/api/jobs/{job_id}/parameters_display", data={"hda_ldda": "hda"}
        )
        self._assert_status_code_is(display_parameters_by_job_response, 200)
        display_parameters_by_dataset_response = self._get(
            f"/api/datasets/{dataset_id}/parameters_display", data={"hda_ldda": "hda"}
        )
        self._assert_status_code_is(display_parameters_by_dataset_response, 200)

    def _create_and_search_job(self, history_id, inputs, tool_id):
        # create a job
        search_payload = self._search_payload(history_id=history_id, tool_id=tool_id, inputs=inputs)
        tool_response = self._post("tools", data=search_payload)
        self.dataset_populator.wait_for_tool_run(history_id, run_response=tool_response)
        # search for the job and get the corresponding values
        search_response = self._post("jobs/search", data=search_payload, json=True)
        self._assert_status_code_is(search_response, 200)
        return search_response

    def _job_search(self, tool_id, history_id, inputs):
        search_payload = self._search_payload(history_id=history_id, tool_id=tool_id, inputs=inputs)
        empty_search_response = self._post("jobs/search", data=search_payload, json=True)
        self._assert_status_code_is(empty_search_response, 200)
        assert len(empty_search_response.json()) == 0
        tool_response = self._post("tools", data=search_payload)
        self.dataset_populator.wait_for_tool_run(history_id, run_response=tool_response)
        self._search(search_payload, expected_search_count=1)
        return tool_response

    def _search_payload(self, history_id, tool_id, inputs, state="ok"):
        search_payload = dict(tool_id=tool_id, inputs=inputs, history_id=history_id, state=state)
        return search_payload

    def _search(self, payload, expected_search_count=1):
        # in case job and history aren't updated at exactly the same
        # time give time to wait
        for _ in range(5):
            search_count = self._search_count(payload)
            if search_count == expected_search_count:
                break
            time.sleep(1)
        assert (
            search_count == expected_search_count
        ), f"expected to find {expected_search_count} jobs, got {search_count} jobs"
        return search_count

    def _search_count(self, search_payload):
        search_response = self._post("jobs/search", data=search_payload, json=True)
        self._assert_status_code_is(search_response, 200)
        search_json = search_response.json()
        return len(search_json)

    def __uploads_with_state(self, *states):
        jobs_response = self._get("jobs", data=dict(state=states))
        self._assert_status_code_is(jobs_response, 200)
        jobs = jobs_response.json()
        assert not [j for j in jobs if j["state"] not in states]
        return [j for j in jobs if j["tool_id"] == "__DATA_FETCH__"]

    def __history_with_new_dataset(self, history_id):
        dataset_id = self.dataset_populator.new_dataset(history_id, wait=True)["id"]
        return dataset_id

    def __history_with_ok_dataset(self, history_id):
        dataset_id = self.dataset_populator.new_dataset(history_id, wait=True)["id"]
        return dataset_id

    def __history_with_ok_collection(self, collection_type="list", history_id=None):
        if not history_id:
            history_id = self.dataset_populator.new_history()
        if collection_type == "list":
            fetch_response = self.dataset_collection_populator.create_list_in_history(
                history_id, direct_upload=True
            ).json()
        elif collection_type == "pair":
            fetch_response = self.dataset_collection_populator.create_pair_in_history(
                history_id, direct_upload=True
            ).json()
        elif collection_type == "list:pair":
            fetch_response = self.dataset_collection_populator.create_list_of_pairs_in_history(history_id).json()
        self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
        return fetch_response["outputs"][0]["id"]

    def __jobs_index(self, **kwds):
        jobs_response = self._get("jobs", **kwds)
        self._assert_status_code_is(jobs_response, 200)
        jobs = jobs_response.json()
        assert isinstance(jobs, list)
        return jobs
