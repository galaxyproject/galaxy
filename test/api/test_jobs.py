import datetime
import json
import time
from operator import itemgetter

from base import api
from base.populators import TestsDatasets


class JobsApiTestCase( api.ApiTestCase, TestsDatasets ):

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

        history_id = self._new_history()
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
        self._wait_for_history( history_id, assert_ok=True )

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
        payload = self._run_tool_payload(
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
        payload = self._run_tool_payload(
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
        history_id = self._new_history()
        dataset_id = self._new_dataset( history_id )[ "id" ]
        return history_id, dataset_id

    def __history_with_ok_dataset( self ):
        history_id = self._new_history()
        dataset_id = self._new_dataset( history_id, wait=True )[ "id" ]
        return history_id, dataset_id

    def __jobs_index( self, **kwds ):
        jobs_response = self._get( "jobs", **kwds )
        self._assert_status_code_is( jobs_response, 200 )
        jobs = jobs_response.json()
        assert isinstance( jobs, list )
        return jobs
