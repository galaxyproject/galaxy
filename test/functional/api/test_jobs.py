import json
from operator import itemgetter

from base import api

from .helpers import TestsDatasets


class JobsApiTestCase( api.ApiTestCase, TestsDatasets ):

    def test_index( self ):
        # Create HDA to ensure at least one job exists...
        self.__history_with_new_dataset()
        jobs_response = self._get( "jobs" )

        self._assert_status_code_is( jobs_response, 200 )

        jobs = jobs_response.json()
        assert isinstance( jobs, list )
        assert "upload1" in map( itemgetter( "tool_id" ), jobs )

    def test_index_state_filter( self ):
        # Initial number of ok jobs
        original_count = len( self.__uploads_with_state( "ok" ) )

        # Run through dataset upload to ensure num uplaods at least greater
        # by 1.
        self.__history_with_ok_dataset()

        # Verify number of ok jobs is actually greater.
        new_count = len( self.__uploads_with_state( "ok" ) )
        assert original_count < new_count

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
        assert len( empty_search_response.json() ) == 0

        self.__run_cat_tool( history_id, dataset_id )
        self._wait_for_history( history_id, assert_ok=True )

        self.__assert_one_search_result( search_payload )

    def __assert_one_search_result( self, search_payload ):
        search_response = self._post( "jobs/search", data=search_payload )
        self._assert_status_code_is( search_response, 200 )
        assert len( search_response.json() ) == 1, search_response.json()

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
        history_id, dataset_id = self.__history_with_new_dataset()
        self._wait_for_history( history_id, assert_ok=True )
        return history_id, dataset_id
