import datetime
import json
import os
import time

from operator import itemgetter

from base import api
from base.api_asserts import assert_status_code_is_ok
from base.populators import (
    DatasetPopulator,
    wait_on,
    wait_on_state,
)

from requests import put


class JobsApiTestCase( api.ApiTestCase ):

    def setUp( self ):
        super( JobsApiTestCase, self ).setUp()
        self.dataset_populator = DatasetPopulator( self.galaxy_interactor )

    def test_index( self ):
        # Create HDA to ensure at least one job exists...
        self.__history_with_new_dataset()
        jobs = self.__jobs_index()
        assert "upload1" in map( itemgetter( "tool_id" ), jobs )

    def test_system_details_admin_only( self ):
        self.__history_with_new_dataset()
        jobs = self.__jobs_index( admin=False )
        job = jobs[0]
        self._assert_not_has_keys( job, "command_line", "external_id" )

        jobs = self.__jobs_index( admin=True )
        job = jobs[0]
        self._assert_has_keys( job, "command_line", "external_id" )

    def test_index_state_filter( self ):
        # Initial number of ok jobs
        original_count = len( self.__uploads_with_state( "ok" ) )
        # Run through dataset upload to ensure num uplaods at least greater
        # by 1.
        self.__history_with_ok_dataset()

        # Verify number of ok jobs is actually greater.
        count_increased = False
        for i in range(10):
            new_count = len( self.__uploads_with_state( "ok" ) )
            if original_count < new_count:
                count_increased = True
                break
            time.sleep(.1)

        if not count_increased:
            template = "Jobs in ok state did not increase (was %d, now %d)"
            message = template % (original_count, new_count)
            raise AssertionError(message)

    def test_index_date_filter( self ):
        self.__history_with_new_dataset()
        two_weeks_ago = (datetime.datetime.utcnow() - datetime.timedelta(7)).isoformat()
        last_week = (datetime.datetime.utcnow() - datetime.timedelta(7)).isoformat()
        next_week = (datetime.datetime.utcnow() + datetime.timedelta(7)).isoformat()
        today = datetime.datetime.utcnow().isoformat()
        tomorrow = (datetime.datetime.utcnow() + datetime.timedelta(1)).isoformat()

        jobs = self.__jobs_index( data={"date_range_min": today[0:10], "date_range_max": tomorrow[0:10]} )
        assert len( jobs ) > 0
        today_job_id = jobs[0]["id"]

        jobs = self.__jobs_index( data={"date_range_min": two_weeks_ago, "date_range_max": last_week} )
        assert today_job_id not in map(itemgetter("id"), jobs)

        jobs = self.__jobs_index( data={"date_range_min": last_week, "date_range_max": next_week} )
        assert today_job_id in map(itemgetter("id"), jobs)

    def test_index_history( self ):
        history_id, _ = self.__history_with_new_dataset()
        jobs = self.__jobs_index( data={"history_id": history_id} )
        assert len( jobs ) > 0

        history_id = self.dataset_populator.new_history()
        jobs = self.__jobs_index( data={"history_id": history_id} )
        assert len( jobs ) == 0

    def test_index_multiple_states_filter( self ):
        # Initial number of ok jobs
        original_count = len( self.__uploads_with_state( "ok", "new" ) )

        # Run through dataset upload to ensure num uplaods at least greater
        # by 1.
        self.__history_with_ok_dataset()

        # Verify number of ok jobs is actually greater.
        new_count = len( self.__uploads_with_state( "new", "ok" ) )
        assert original_count < new_count, new_count

    def test_show( self ):
        # Create HDA to ensure at least one job exists...
        self.__history_with_new_dataset()

        jobs_response = self._get( "jobs" )
        first_job = jobs_response.json()[ 0 ]
        self._assert_has_key( first_job, 'id', 'state', 'exit_code', 'update_time', 'create_time' )

        job_id = first_job[ "id" ]
        show_jobs_response = self._get( "jobs/%s" % job_id )
        self._assert_status_code_is( show_jobs_response, 200 )

        job_details = show_jobs_response.json()
        self._assert_has_key( job_details, 'id', 'state', 'exit_code', 'update_time', 'create_time' )

    def test_show_security( self ):
        history_id, _ = self.__history_with_new_dataset()
        jobs_response = self._get( "jobs", data={"history_id": history_id} )
        job = jobs_response.json()[ 0 ]
        job_id = job[ "id" ]

        show_jobs_response = self._get( "jobs/%s" % job_id, admin=False )
        self._assert_not_has_keys( show_jobs_response.json(), "command_line", "external_id" )

        # TODO: Re-activate test case when API accepts privacy settings
        # with self._different_user():
        #    show_jobs_response = self._get( "jobs/%s" % job_id, admin=False )
        #    self._assert_status_code_is( show_jobs_response, 200 )

        show_jobs_response = self._get( "jobs/%s" % job_id, admin=True )
        self._assert_has_keys( show_jobs_response.json(), "command_line", "external_id" )

    def test_deleting_output_keep_running_until_all_deleted( self ):
        history_id, job_state, outputs = self._setup_running_two_output_job( 60 )

        # Delete one of the two outputs and make sure the job is still running.
        self._raw_update_history_item( history_id, outputs[0]["id"], {"deleted": True} )
        time.sleep( 1 )
        state = job_state().json()["state"]
        assert state == "running", state

        # Delete the second output and make sure the job is cancelled.
        self._raw_update_history_item( history_id, outputs[1]["id"], {"deleted": True} )
        final_state = wait_on_state( job_state, assert_ok=False, timeout=15 )
        assert final_state in ["deleted_new", "deleted"], final_state

    def test_purging_output_keep_running_until_all_purged( self ):
        history_id, job_state, outputs = self._setup_running_two_output_job( 60 )

        # Pretty much right away after the job is running, these paths should be populated -
        # if they are grab them and make sure they are deleted at the end of the job.
        dataset_1 = self._get_history_item_as_admin( history_id, outputs[0]["id"] )
        dataset_2 = self._get_history_item_as_admin( history_id, outputs[1]["id"] )
        if "file_name" in dataset_1:
            output_dataset_paths = [ dataset_1[ "file_name" ], dataset_2[ "file_name" ] ]
            # This may or may not exist depending on if the test is local or not.
            output_dataset_paths_exist = os.path.exists( output_dataset_paths[ 0 ] )
        else:
            output_dataset_paths = []
            output_dataset_paths_exist = False

        current_state = job_state().json()["state"]
        assert current_state == "running", current_state

        # Purge one of the two outputs and make sure the job is still running.
        self._raw_update_history_item( history_id, outputs[0]["id"], {"purged": True} )
        time.sleep( 1 )
        current_state = job_state().json()["state"]
        assert current_state == "running", current_state

        # Purge the second output and make sure the job is cancelled.
        self._raw_update_history_item( history_id, outputs[1]["id"], {"purged": True} )
        final_state = wait_on_state( job_state, assert_ok=False, timeout=15 )
        assert final_state in ["deleted_new", "deleted"], final_state

        def paths_deleted():
            if not os.path.exists( output_dataset_paths[ 0 ] ) and not os.path.exists( output_dataset_paths[ 1 ] ):
                return True

        if output_dataset_paths_exist:
            wait_on(paths_deleted, "path deletion")

    def test_purging_output_cleaned_after_ok_run( self ):
        history_id, job_state, outputs = self._setup_running_two_output_job( 10 )

        # Pretty much right away after the job is running, these paths should be populated -
        # if they are grab them and make sure they are deleted at the end of the job.
        dataset_1 = self._get_history_item_as_admin( history_id, outputs[0]["id"] )
        dataset_2 = self._get_history_item_as_admin( history_id, outputs[1]["id"] )
        if "file_name" in dataset_1:
            output_dataset_paths = [ dataset_1[ "file_name" ], dataset_2[ "file_name" ] ]
            # This may or may not exist depending on if the test is local or not.
            output_dataset_paths_exist = os.path.exists( output_dataset_paths[ 0 ] )
        else:
            output_dataset_paths = []
            output_dataset_paths_exist = False

        if not output_dataset_paths_exist:
            # Given this Galaxy configuration - there is nothing more to be tested here.
            # Consider throwing a skip instead.
            return

        # Purge one of the two outputs and wait for the job to complete.
        self._raw_update_history_item( history_id, outputs[0]["id"], {"purged": True} )
        wait_on_state(job_state, assert_ok=True)

        if output_dataset_paths_exist:
            time.sleep( .5 )
            # Make sure the non-purged dataset is on disk and the purged one is not.
            assert os.path.exists( output_dataset_paths[ 1 ] )
            assert not os.path.exists( output_dataset_paths[ 0 ] )

    def _setup_running_two_output_job( self, sleep_time ):
        history_id = self.dataset_populator.new_history()
        payload = self.dataset_populator.run_tool_payload(
            tool_id='create_2',
            inputs=dict(
                sleep_time=sleep_time,
            ),
            history_id=history_id,
        )
        run_response = self._post( "tools", data=payload ).json()
        outputs = run_response[ "outputs" ]
        jobs = run_response[ "jobs" ]

        assert len(outputs) == 2
        assert len(jobs) == 1

        def job_state():
            jobs_response = self._get( "jobs/%s" % jobs[0]["id"] )
            return jobs_response

        # Give job some time to get up and running.
        time.sleep( 2 )
        running_state = wait_on_state( job_state, skip_states=["queued", "new"], assert_ok=False, timeout=15 )
        assert running_state == "running", running_state

        def job_state():
            jobs_response = self._get( "jobs/%s" % jobs[0]["id"] )
            return jobs_response

        return history_id, job_state, outputs

    def _raw_update_history_item( self, history_id, item_id, data ):
        update_url = self._api_url( "histories/%s/contents/%s" % (history_id, item_id), use_key=True)
        update_response = put(update_url, json=data)
        assert_status_code_is_ok( update_response )
        return update_response

    def _get_history_item_as_admin( self, history_id, item_id ):
        response = self._get( "histories/%s/contents/%s?view=detailed" % (history_id, item_id), admin=True )
        assert_status_code_is_ok( response )
        return response.json()

    def test_search( self ):
        history_id, dataset_id = self.__history_with_ok_dataset()

        inputs = json.dumps(
            dict(
                input1=dict(
                    src='hda',
                    id=dataset_id,
                )
            )
        )
        search_payload = dict(
            tool_id="cat1",
            inputs=inputs,
            state="ok",
        )

        empty_search_response = self._post( "jobs/search", data=search_payload )
        self._assert_status_code_is( empty_search_response, 200 )
        self.assertEquals( len( empty_search_response.json() ), 0 )

        self.__run_cat_tool( history_id, dataset_id )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )

        search_count = -1
        # in case job and history aren't updated at exactly the same
        # time give time to wait
        for i in range(5):
            search_count = self._search_count(search_payload)
            if search_count == 1:
                break
            time.sleep(.1)

        self.assertEquals( search_count, 1 )

    def _search_count( self, search_payload ):
        search_response = self._post( "jobs/search", data=search_payload )
        self._assert_status_code_is( search_response, 200 )
        search_json = search_response.json()
        return len(search_json)

    def __run_cat_tool( self, history_id, dataset_id ):
        # Code duplication with test_jobs.py, eliminate
        payload = self.dataset_populator.run_tool_payload(
            tool_id='cat1',
            inputs=dict(
                input1=dict(
                    src='hda',
                    id=dataset_id
                ),
            ),
            history_id=history_id,
        )
        self._post( "tools", data=payload )

    def __run_randomlines_tool( self, lines, history_id, dataset_id ):
        payload = self.dataset_populator.run_tool_payload(
            tool_id="random_lines1",
            inputs=dict(
                num_lines=lines,
                input=dict(
                    src='hda',
                    id=dataset_id,
                ),
            ),
            history_id=history_id,
        )
        self._post( "tools", data=payload )

    def __uploads_with_state( self, *states ):
        jobs_response = self._get( "jobs", data=dict( state=states ) )
        self._assert_status_code_is( jobs_response, 200 )
        jobs = jobs_response.json()
        assert not filter( lambda j: j[ "state" ] not in states, jobs )
        return filter( lambda j: j[ "tool_id" ] == "upload1", jobs )

    def __history_with_new_dataset( self ):
        history_id = self.dataset_populator.new_history()
        dataset_id = self.dataset_populator.new_dataset( history_id )[ "id" ]
        return history_id, dataset_id

    def __history_with_ok_dataset( self ):
        history_id = self.dataset_populator.new_history()
        dataset_id = self.dataset_populator.new_dataset( history_id, wait=True )[ "id" ]
        return history_id, dataset_id

    def __jobs_index( self, **kwds ):
        jobs_response = self._get( "jobs", **kwds )
        self._assert_status_code_is( jobs_response, 200 )
        jobs = jobs_response.json()
        assert isinstance( jobs, list )
        return jobs
