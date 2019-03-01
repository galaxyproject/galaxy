import datetime
import json
import os
import time
from operator import itemgetter

import requests

from base import api  # noqa: I100,I202
from base.api_asserts import assert_status_code_is_ok  # noqa: I100
from base.populators import (  # noqa: I100
    DatasetCollectionPopulator,
    DatasetPopulator,
    skip_without_tool,
    uses_test_history,
    wait_on,
    wait_on_state,
)


class JobsApiTestCase(api.ApiTestCase):

    def setUp(self):
        super(JobsApiTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    @uses_test_history(require_new=True)
    def test_index(self, history_id):
        # Create HDA to ensure at least one job exists...
        self.__history_with_new_dataset(history_id)
        jobs = self.__jobs_index()
        assert "upload1" in map(itemgetter("tool_id"), jobs)

    @uses_test_history(require_new=True)
    def test_system_details_admin_only(self, history_id):
        self.__history_with_new_dataset(history_id)
        jobs = self.__jobs_index(admin=False)
        job = jobs[0]
        self._assert_not_has_keys(job, "command_line", "external_id")

        jobs = self.__jobs_index(admin=True)
        job = jobs[0]
        self._assert_has_keys(job, "command_line", "external_id")

    @uses_test_history(require_new=True)
    def test_index_state_filter(self, history_id):
        # Initial number of ok jobs
        original_count = len(self.__uploads_with_state("ok"))
        # Run through dataset upload to ensure num uplaods at least greater
        # by 1.
        self.__history_with_ok_dataset(history_id)

        # Verify number of ok jobs is actually greater.
        count_increased = False
        for i in range(10):
            new_count = len(self.__uploads_with_state("ok"))
            if original_count < new_count:
                count_increased = True
                break
            time.sleep(.1)

        if not count_increased:
            template = "Jobs in ok state did not increase (was %d, now %d)"
            message = template % (original_count, new_count)
            raise AssertionError(message)

    @uses_test_history(require_new=True)
    def test_index_date_filter(self, history_id):
        self.__history_with_new_dataset(history_id)
        two_weeks_ago = (datetime.datetime.utcnow() - datetime.timedelta(7)).isoformat()
        last_week = (datetime.datetime.utcnow() - datetime.timedelta(7)).isoformat()
        next_week = (datetime.datetime.utcnow() + datetime.timedelta(7)).isoformat()
        today = datetime.datetime.utcnow().isoformat()
        tomorrow = (datetime.datetime.utcnow() + datetime.timedelta(1)).isoformat()

        jobs = self.__jobs_index(data={"date_range_min": today[0:10], "date_range_max": tomorrow[0:10]})
        assert len(jobs) > 0
        today_job_id = jobs[0]["id"]

        jobs = self.__jobs_index(data={"date_range_min": two_weeks_ago, "date_range_max": last_week})
        assert today_job_id not in map(itemgetter("id"), jobs)

        jobs = self.__jobs_index(data={"date_range_min": last_week, "date_range_max": next_week})
        assert today_job_id in map(itemgetter("id"), jobs)

    @uses_test_history(require_new=True)
    def test_index_history(self, history_id):
        self.__history_with_new_dataset(history_id)
        jobs = self.__jobs_index(data={"history_id": history_id})
        assert len(jobs) > 0

        with self.dataset_populator.test_history() as other_history_id:
            jobs = self.__jobs_index(data={"history_id": other_history_id})
            assert len(jobs) == 0

    @uses_test_history(require_new=True)
    def test_index_multiple_states_filter(self, history_id):
        # Initial number of ok jobs
        original_count = len(self.__uploads_with_state("ok", "new"))

        # Run through dataset upload to ensure num uplaods at least greater
        # by 1.
        self.__history_with_ok_dataset(history_id)

        # Verify number of ok jobs is actually greater.
        new_count = len(self.__uploads_with_state("new", "ok"))
        assert original_count < new_count, new_count

    @uses_test_history(require_new=True)
    def test_show(self, history_id):
        # Create HDA to ensure at least one job exists...
        self.__history_with_new_dataset(history_id)

        jobs_response = self._get("jobs")
        first_job = jobs_response.json()[0]
        self._assert_has_key(first_job, 'id', 'state', 'exit_code', 'update_time', 'create_time')

        job_id = first_job["id"]
        show_jobs_response = self._get("jobs/%s" % job_id)
        self._assert_status_code_is(show_jobs_response, 200)

        job_details = show_jobs_response.json()
        self._assert_has_key(job_details, 'id', 'state', 'exit_code', 'update_time', 'create_time')

    @uses_test_history(require_new=True)
    def test_show_security(self, history_id):
        self.__history_with_new_dataset(history_id)
        jobs_response = self._get("jobs", data={"history_id": history_id})
        job = jobs_response.json()[0]
        job_id = job["id"]

        show_jobs_response = self._get("jobs/%s" % job_id, admin=False)
        self._assert_not_has_keys(show_jobs_response.json(), "command_line", "external_id")

        # TODO: Re-activate test case when API accepts privacy settings
        # with self._different_user():
        #    show_jobs_response = self._get( "jobs/%s" % job_id, admin=False )
        #    self._assert_status_code_is( show_jobs_response, 200 )

        show_jobs_response = self._get("jobs/%s" % job_id, admin=True)
        self._assert_has_keys(show_jobs_response.json(), "command_line", "external_id")

    @skip_without_tool('detect_errors_aggressive')
    def test_report_error(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.run_tool_payload(
                tool_id='detect_errors_aggressive',
                inputs={'error_bool': 'true'},
                history_id=history_id,
            )
            run_response = self._post("tools", data=payload).json()
            job_id = run_response['jobs'][0]["id"]
            dataset_id = run_response['outputs'][0]['id']
            response = self._post('jobs/%s/error' % job_id,
                                  data={'dataset_id': dataset_id})
            assert response.status_code == 200

    @skip_without_tool('detect_errors_aggressive')
    def test_report_error_anon(self):
        # Need to get a cookie and use that for anonymous tool runs
        cookies = requests.get(self.url).cookies
        payload = json.dumps({"tool_id": "detect_errors_aggressive",
                              "inputs": {"error_bool": "true"}})
        run_response = requests.post("%s/tools" % self.galaxy_interactor.api_url, data=payload, cookies=cookies).json()
        job_id = run_response['jobs'][0]["id"]
        dataset_id = run_response['outputs'][0]['id']
        response = requests.post('%s/jobs/%s/error' % (self.galaxy_interactor.api_url, job_id),
                                 params={'email': 'someone@domain.com', 'dataset_id': dataset_id},
                                 cookies=cookies)
        assert response.status_code == 200

    @uses_test_history(require_new=True)
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
        assert final_state in ["deleted_new", "deleted"], final_state

    @uses_test_history(require_new=True)
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
        assert final_state in ["deleted_new", "deleted"], final_state

        def paths_deleted():
            if not os.path.exists(output_dataset_paths[0]) and not os.path.exists(output_dataset_paths[1]):
                return True

        if output_dataset_paths_exist:
            wait_on(paths_deleted, "path deletion")

    @uses_test_history(require_new=True)
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
            time.sleep(.5)
            # Make sure the non-purged dataset is on disk and the purged one is not.
            assert os.path.exists(output_dataset_paths[1])
            assert not os.path.exists(output_dataset_paths[0])

    def _hack_to_skip_test_if_state_ok(self, job_state):
        from nose.plugins.skip import SkipTest
        if job_state().json()["state"] == "ok":
            message = "Job state switch from running to ok too quickly - the rest of the test requires the job to be in a running state. Skipping test."
            raise SkipTest(message)

    def _setup_running_two_output_job(self, history_id, sleep_time):
        payload = self.dataset_populator.run_tool_payload(
            tool_id='create_2',
            inputs=dict(
                sleep_time=sleep_time,
            ),
            history_id=history_id,
        )
        run_response = self._post("tools", data=payload).json()
        outputs = run_response["outputs"]
        jobs = run_response["jobs"]

        assert len(outputs) == 2
        assert len(jobs) == 1

        def job_state():
            jobs_response = self._get("jobs/%s" % jobs[0]["id"])
            return jobs_response

        # Give job some time to get up and running.
        time.sleep(2)
        running_state = wait_on_state(job_state, skip_states=["queued", "new"], assert_ok=False, timeout=15)
        assert running_state == "running", running_state

        def job_state():
            jobs_response = self._get("jobs/%s" % jobs[0]["id"])
            return jobs_response

        return job_state, outputs

    def _raw_update_history_item(self, history_id, item_id, data):
        update_url = self._api_url("histories/%s/contents/%s" % (history_id, item_id), use_key=True)
        update_response = requests.put(update_url, json=data)
        assert_status_code_is_ok(update_response)
        return update_response

    @skip_without_tool("cat_data_and_sleep")
    @uses_test_history(require_new=True)
    def test_resume_job(self, history_id):
        hda1 = self.dataset_populator.new_dataset(history_id, content="samp1\t10.0\nsamp2\t20.0\n")
        hda2 = self.dataset_populator.new_dataset(history_id, content="samp1\t30.0\nsamp2\t40.0\n")
        # Submit first job
        payload = self.dataset_populator.run_tool_payload(
            tool_id='cat_data_and_sleep',
            inputs={
                'sleep_time': 15,
                'input1': {'src': 'hda', 'id': hda2['id']},
                'queries_0|input2': {'src': 'hda', 'id': hda2['id']}
            },
            history_id=history_id,
        )
        run_response = self._post("tools", data=payload).json()
        output = run_response["outputs"][0]
        # Submit second job that waits on job1
        payload = self.dataset_populator.run_tool_payload(
            tool_id='cat1',
            inputs={
                'input1': {'src': 'hda', 'id': hda1['id']},
                'queries_0|input2': {'src': 'hda', 'id': output['id']}
            },
            history_id=history_id,
        )
        run_response = self._post("tools", data=payload).json()
        job_id = run_response['jobs'][0]['id']
        output = run_response["outputs"][0]
        # Delete second jobs input while second job is waiting for first job
        delete_response = self._delete("histories/%s/contents/%s" % (history_id, hda1['id']))
        self._assert_status_code_is(delete_response, 200)
        self.dataset_populator.wait_for_history_jobs(history_id, assert_ok=False)
        dataset_details = self._get("histories/%s/contents/%s" % (history_id, output['id'])).json()
        assert dataset_details['state'] == 'paused'
        # Undelete input dataset
        undelete_response = self._put("histories/%s/contents/%s" % (history_id, hda1['id']),
                                      data=json.dumps({'deleted': False}))
        self._assert_status_code_is(undelete_response, 200)
        resume_response = self._put("jobs/%s/resume" % job_id)
        self._assert_status_code_is(resume_response, 200)
        self.dataset_populator.wait_for_history_jobs(history_id, assert_ok=True)
        dataset_details = self._get("histories/%s/contents/%s" % (history_id, output['id'])).json()
        assert dataset_details['state'] == 'ok'

    def _get_history_item_as_admin(self, history_id, item_id):
        response = self._get("histories/%s/contents/%s?view=detailed" % (history_id, item_id), admin=True)
        assert_status_code_is_ok(response)
        return response.json()

    @uses_test_history(require_new=True)
    def test_search(self, history_id):
        dataset_id = self.__history_with_ok_dataset(history_id)
        # We first copy the datasets, so that the update time is lower than the job creation time
        new_history_id = self.dataset_populator.new_history()
        copy_payload = {"content": dataset_id, "source": "hda", "type": "dataset"}
        copy_response = self._post("histories/%s/contents" % new_history_id, data=copy_payload)
        self._assert_status_code_is(copy_response, 200)
        inputs = json.dumps({
            'input1': {'src': 'hda', 'id': dataset_id}
        })
        self._job_search(tool_id='cat1', history_id=history_id, inputs=inputs)
        # We test that a job can be found even if the dataset has been copied to another history
        new_dataset_id = copy_response.json()['id']
        copied_inputs = json.dumps({
            'input1': {'src': 'hda', 'id': new_dataset_id}
        })
        search_payload = self._search_payload(history_id=history_id, tool_id='cat1', inputs=copied_inputs)
        self._search(search_payload, expected_search_count=1)
        # Now we delete the original input HDA that was used -- we should still be able to find the job
        delete_respone = self._delete("histories/%s/contents/%s" % (history_id, dataset_id))
        self._assert_status_code_is(delete_respone, 200)
        self._search(search_payload, expected_search_count=1)
        # Now we also delete the copy -- we shouldn't find a job
        delete_respone = self._delete("histories/%s/contents/%s" % (new_history_id, new_dataset_id))
        self._assert_status_code_is(delete_respone, 200)
        self._search(search_payload, expected_search_count=0)

    @uses_test_history(require_new=True)
    def test_search_handle_identifiers(self, history_id):
        # Test that input name and element identifier of a jobs' output must match for a job to be returned.
        dataset_id = self.__history_with_ok_dataset(history_id)
        inputs = json.dumps({
            'input1': {'src': 'hda', 'id': dataset_id}
        })
        self._job_search(tool_id='identifier_single', history_id=history_id, inputs=inputs)
        dataset_details = self._get("histories/%s/contents/%s" % (history_id, dataset_id)).json()
        dataset_details['name'] = 'Renamed Test Dataset'
        dataset_update_response = self._put("histories/%s/contents/%s" % (history_id, dataset_id), data=dict(name='Renamed Test Dataset'))
        self._assert_status_code_is(dataset_update_response, 200)
        assert dataset_update_response.json()['name'] == 'Renamed Test Dataset'
        search_payload = self._search_payload(history_id=history_id, tool_id='identifier_single', inputs=inputs)
        self._search(search_payload, expected_search_count=0)

    @uses_test_history(require_new=True)
    def test_search_delete_outputs(self, history_id):
        dataset_id = self.__history_with_ok_dataset(history_id)
        inputs = json.dumps({
            'input1': {'src': 'hda', 'id': dataset_id}
        })
        tool_response = self._job_search(tool_id='cat1', history_id=history_id, inputs=inputs)
        output_id = tool_response.json()['outputs'][0]['id']
        delete_respone = self._delete("histories/%s/contents/%s" % (history_id, output_id))
        self._assert_status_code_is(delete_respone, 200)
        search_payload = self._search_payload(history_id=history_id, tool_id='cat1', inputs=inputs)
        self._search(search_payload, expected_search_count=0)

    @uses_test_history(require_new=True)
    def test_search_with_hdca_list_input(self, history_id):
        list_id_a = self.__history_with_ok_collection(collection_type='list', history_id=history_id)
        list_id_b = self.__history_with_ok_collection(collection_type='list', history_id=history_id)
        inputs = json.dumps({
            'f1': {'src': 'hdca', 'id': list_id_a},
            'f2': {'src': 'hdca', 'id': list_id_b},
        })
        tool_response = self._job_search(tool_id='multi_data_param', history_id=history_id, inputs=inputs)
        # We switch the inputs, this should not return a match
        inputs_switched = json.dumps({
            'f2': {'src': 'hdca', 'id': list_id_a},
            'f1': {'src': 'hdca', 'id': list_id_b},
        })
        search_payload = self._search_payload(history_id=history_id, tool_id='multi_data_param', inputs=inputs_switched)
        self._search(search_payload, expected_search_count=0)
        # We delete the ouput (this is a HDA, as multi_data_param reduces collections)
        # and use the correct input job definition, the job should not be found
        output_id = tool_response.json()['outputs'][0]['id']
        delete_respone = self._delete("histories/%s/contents/%s" % (history_id, output_id))
        self._assert_status_code_is(delete_respone, 200)
        search_payload = self._search_payload(history_id=history_id, tool_id='multi_data_param', inputs=inputs)
        self._search(search_payload, expected_search_count=0)

    @uses_test_history(require_new=True)
    def test_search_delete_hdca_output(self, history_id):
        list_id_a = self.__history_with_ok_collection(collection_type='list', history_id=history_id)
        inputs = json.dumps({
            'input1': {'src': 'hdca', 'id': list_id_a},
        })
        tool_response = self._job_search(tool_id='collection_creates_list', history_id=history_id, inputs=inputs)
        output_id = tool_response.json()['outputs'][0]['id']
        # We delete a single tool output, no job should be returned
        delete_respone = self._delete("histories/%s/contents/%s" % (history_id, output_id))
        self._assert_status_code_is(delete_respone, 200)
        search_payload = self._search_payload(history_id=history_id, tool_id='collection_creates_list', inputs=inputs)
        self._search(search_payload, expected_search_count=0)
        tool_response = self._job_search(tool_id='collection_creates_list', history_id=history_id, inputs=inputs)
        output_collection_id = tool_response.json()['output_collections'][0]['id']
        # We delete a collection output, no job should be returned
        delete_respone = self._delete("histories/%s/contents/dataset_collections/%s" % (history_id, output_collection_id))
        self._assert_status_code_is(delete_respone, 200)
        search_payload = self._search_payload(history_id=history_id, tool_id='collection_creates_list', inputs=inputs)
        self._search(search_payload, expected_search_count=0)

    @uses_test_history(require_new=True)
    def test_search_with_hdca_pair_input(self, history_id):
        list_id_a = self.__history_with_ok_collection(collection_type='pair', history_id=history_id)
        inputs = json.dumps({
            'f1': {'src': 'hdca', 'id': list_id_a},
            'f2': {'src': 'hdca', 'id': list_id_a},
        })
        self._job_search(tool_id='multi_data_param', history_id=history_id, inputs=inputs)
        # We test that a job can be found even if the collection has been copied to another history
        new_history_id = self.dataset_populator.new_history()
        copy_payload = {"content": list_id_a, "source": "hdca", "type": "dataset_collection"}
        copy_response = self._post("histories/%s/contents" % new_history_id, data=copy_payload)
        self._assert_status_code_is(copy_response, 200)
        new_list_a = copy_response.json()['id']
        copied_inputs = json.dumps({
            'f1': {'src': 'hdca', 'id': new_list_a},
            'f2': {'src': 'hdca', 'id': new_list_a},
        })
        search_payload = self._search_payload(history_id=new_history_id, tool_id='multi_data_param', inputs=copied_inputs)
        self._search(search_payload, expected_search_count=1)
        # Now we delete the original input HDCA that was used -- we should still be able to find the job
        delete_respone = self._delete("histories/%s/contents/dataset_collections/%s" % (history_id, list_id_a))
        self._assert_status_code_is(delete_respone, 200)
        self._search(search_payload, expected_search_count=1)
        # Now we also delete the copy -- we shouldn't find a job
        delete_respone = self._delete("histories/%s/contents/dataset_collections/%s" % (history_id, new_list_a))
        self._assert_status_code_is(delete_respone, 200)
        self._search(search_payload, expected_search_count=0)

    @uses_test_history(require_new=True)
    def test_search_with_hdca_list_pair_input(self, history_id):
        list_id_a = self.__history_with_ok_collection(collection_type='list:pair', history_id=history_id)
        inputs = json.dumps({
            'f1': {'src': 'hdca', 'id': list_id_a},
            'f2': {'src': 'hdca', 'id': list_id_a},
        })
        self._job_search(tool_id='multi_data_param', history_id=history_id, inputs=inputs)

    def _job_search(self, tool_id, history_id, inputs):
        search_payload = self._search_payload(history_id=history_id, tool_id=tool_id, inputs=inputs)
        empty_search_response = self._post("jobs/search", data=search_payload)
        self._assert_status_code_is(empty_search_response, 200)
        self.assertEqual(len(empty_search_response.json()), 0)
        tool_response = self._post("tools", data=search_payload)
        self.dataset_populator.wait_for_tool_run(history_id, run_response=tool_response)
        self._search(search_payload, expected_search_count=1)
        return tool_response

    def _search_payload(self, history_id, tool_id, inputs, state='ok'):
        search_payload = dict(
            tool_id=tool_id,
            inputs=inputs,
            history_id=history_id,
            state=state
        )
        return search_payload

    def _search(self, payload, expected_search_count=1):
        # in case job and history aren't updated at exactly the same
        # time give time to wait
        for i in range(5):
            search_count = self._search_count(payload)
            if search_count == expected_search_count:
                break
            time.sleep(1)
        assert search_count == expected_search_count, "expected to find %d jobs, got %d jobs" % (expected_search_count, search_count)
        return search_count

    def _search_count(self, search_payload):
        search_response = self._post("jobs/search", data=search_payload)
        self._assert_status_code_is(search_response, 200)
        search_json = search_response.json()
        return len(search_json)

    def __uploads_with_state(self, *states):
        jobs_response = self._get("jobs", data=dict(state=states))
        self._assert_status_code_is(jobs_response, 200)
        jobs = jobs_response.json()
        assert not [j for j in jobs if not j['state'] in states]
        return [j for j in jobs if j['tool_id'] == 'upload1']

    def __history_with_new_dataset(self, history_id):
        dataset_id = self.dataset_populator.new_dataset(history_id)["id"]
        return dataset_id

    def __history_with_ok_dataset(self, history_id):
        dataset_id = self.dataset_populator.new_dataset(history_id, wait=True)["id"]
        return dataset_id

    def __history_with_ok_collection(self, collection_type='list', history_id=None):
        if not history_id:
            history_id = self.dataset_populator.new_history()
        if collection_type == 'list':
            fetch_response = self.dataset_collection_populator.create_list_in_history(history_id, direct_upload=True).json()
        elif collection_type == 'pair':
            fetch_response = self.dataset_collection_populator.create_pair_in_history(history_id, direct_upload=True).json()
        elif collection_type == 'list:pair':
            fetch_response = self.dataset_collection_populator.create_list_of_pairs_in_history(history_id).json()
        self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
        return fetch_response["outputs"][0]['id']

    def __jobs_index(self, **kwds):
        jobs_response = self._get("jobs", **kwds)
        self._assert_status_code_is(jobs_response, 200)
        jobs = jobs_response.json()
        assert isinstance(jobs, list)
        return jobs
