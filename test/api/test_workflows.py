from base import api
from json import dumps
from json import loads
import operator
import time
from .helpers import WorkflowPopulator
from .helpers import DatasetPopulator
from .helpers import DatasetCollectionPopulator
from .helpers import skip_without_tool

from requests import delete

from galaxy.exceptions import error_codes


# Workflow API TODO:
# - Allow history_id as param to workflow run action. (hist_id)
# - Allow post to workflows/<workflow_id>/run in addition to posting to
#    /workflows with id in payload.
# - Much more testing obviously, always more testing.
class WorkflowsApiTestCase( api.ApiTestCase ):

    def setUp( self ):
        super( WorkflowsApiTestCase, self ).setUp()
        self.workflow_populator = WorkflowPopulator( self.galaxy_interactor )
        self.dataset_populator = DatasetPopulator( self.galaxy_interactor )
        self.dataset_collection_populator = DatasetCollectionPopulator( self.galaxy_interactor )

    def test_show_invalid_key_is_400( self ):
        show_response = self._get( "workflows/%s" % self._random_key() )
        self._assert_status_code_is( show_response, 400 )

    def test_cannot_show_private_workflow( self ):
        workflow_id = self.workflow_populator.simple_workflow( "test_not_importportable" )
        with self._different_user():
            show_response = self._get( "workflows/%s" % workflow_id )
            self._assert_status_code_is( show_response, 403 )

    def test_delete( self ):
        workflow_id = self.workflow_populator.simple_workflow( "test_delete" )
        workflow_name = "test_delete (imported from API)"
        self._assert_user_has_workflow_with_name( workflow_name )
        workflow_url = self._api_url( "workflows/%s" % workflow_id, use_key=True )
        delete_response = delete( workflow_url )
        self._assert_status_code_is( delete_response, 200 )
        # Make sure workflow is no longer in index by default.
        assert workflow_name not in self.__workflow_names()

    def test_other_cannot_delete( self ):
        workflow_id = self.workflow_populator.simple_workflow( "test_other_delete" )
        with self._different_user():
            workflow_url = self._api_url( "workflows/%s" % workflow_id, use_key=True )
            delete_response = delete( workflow_url )
            self._assert_status_code_is( delete_response, 403 )

    def test_index( self ):
        index_response = self._get( "workflows" )
        self._assert_status_code_is( index_response, 200 )
        assert isinstance( index_response.json(), list )

    def test_upload( self ):
        self.__test_upload( use_deprecated_route=False )

    def test_upload_deprecated( self ):
        self.__test_upload( use_deprecated_route=True )

    def __test_upload( self, use_deprecated_route ):
        data = dict(
            workflow=dumps( self.workflow_populator.load_workflow( name="test_import" ) ),
        )
        if use_deprecated_route:
            route = "workflows/upload"
        else:
            route = "workflows"
        upload_response = self._post( route, data=data )
        self._assert_status_code_is( upload_response, 200 )
        self._assert_user_has_workflow_with_name( "test_import (imported from API)" )

    def test_import_deprecated( self ):
        workflow_id = self.workflow_populator.simple_workflow( "test_import_published_deprecated", publish=True )
        with self._different_user():
            other_import_response = self.__import_workflow( workflow_id )
            self._assert_status_code_is( other_import_response, 200 )
            self._assert_user_has_workflow_with_name( "imported: test_import_published_deprecated (imported from API)")

    def test_not_importable_prevents_import( self ):
        workflow_id = self.workflow_populator.simple_workflow( "test_not_importportable" )
        with self._different_user():
            other_import_response = self.__import_workflow( workflow_id )
            self._assert_status_code_is( other_import_response, 403 )

    def test_import_published( self ):
        workflow_id = self.workflow_populator.simple_workflow( "test_import_published", publish=True )
        with self._different_user():
            other_import_response = self.__import_workflow( workflow_id, deprecated_route=True )
            self._assert_status_code_is( other_import_response, 200 )
            self._assert_user_has_workflow_with_name( "imported: test_import_published (imported from API)")

    def test_export( self ):
        uploaded_workflow_id = self.workflow_populator.simple_workflow( "test_for_export" )
        download_response = self._get( "workflows/%s/download" % uploaded_workflow_id )
        self._assert_status_code_is( download_response, 200 )
        downloaded_workflow = download_response.json()
        assert downloaded_workflow[ "name" ] == "test_for_export (imported from API)"
        assert len( downloaded_workflow[ "steps" ] ) == 3
        first_input = downloaded_workflow[ "steps" ][ "0" ][ "inputs" ][ 0 ]
        assert first_input[ "name" ] == "WorkflowInput1"
        assert first_input[ "description" ] == "input1 description"

    def test_import_export_with_runtime_inputs( self ):
        workflow = self.workflow_populator.load_workflow_from_resource( name="test_workflow_with_runtime_input" )
        workflow_id = self.workflow_populator.create_workflow( workflow )
        download_response = self._get( "workflows/%s/download" % workflow_id )
        downloaded_workflow = download_response.json()
        assert len( downloaded_workflow[ "steps" ] ) == 2
        runtime_input = downloaded_workflow[ "steps" ][ "1" ][ "inputs" ][ 0 ]
        assert runtime_input[ "description" ].startswith( "runtime parameter for tool" )
        assert runtime_input[ "name" ] == "num_lines"

    @skip_without_tool( "cat1" )
    def test_run_workflow_by_index( self ):
        self.__run_cat_workflow( inputs_by='step_index' )

    @skip_without_tool( "cat1" )
    def test_run_workflow_by_name( self ):
        self.__run_cat_workflow( inputs_by='name' )

    @skip_without_tool( "cat1" )
    def test_run_workflow( self ):
        self.__run_cat_workflow( inputs_by='step_id' )

    def __run_cat_workflow( self, inputs_by ):
        workflow = self.workflow_populator.load_workflow( name="test_for_run" )
        workflow_request, history_id = self._setup_workflow_run( workflow, inputs_by=inputs_by )
        # TODO: This should really be a post to workflows/<workflow_id>/run or
        # something like that.
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )

    def test_cannot_run_inaccessible_workflow( self ):
        workflow = self.workflow_populator.load_workflow( name="test_for_run_cannot_access" )
        workflow_request, history_id = self._setup_workflow_run( workflow )
        with self._different_user():
            run_workflow_response = self._post( "workflows", data=workflow_request )
            self._assert_status_code_is( run_workflow_response, 403 )

    def test_400_on_invalid_workflow_id( self ):
        workflow = self.workflow_populator.load_workflow( name="test_for_run_does_not_exist" )
        workflow_request, history_id = self._setup_workflow_run( workflow )
        workflow_request[ "workflow_id" ] = self._random_key()
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 400 )

    def test_cannot_run_against_other_users_history( self ):
        workflow = self.workflow_populator.load_workflow( name="test_for_run_does_not_exist" )
        workflow_request, history_id = self._setup_workflow_run( workflow )
        with self._different_user():
            other_history_id = self.dataset_populator.new_history()
        workflow_request[ "history" ] = "hist_id=%s" % other_history_id
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 403 )

    @skip_without_tool( "cat" )
    @skip_without_tool( "cat_list" )
    def test_workflow_run_with_matching_lists( self ):
        workflow = self.workflow_populator.load_workflow_from_resource( "test_workflow_matching_lists" )
        workflow_id = self.workflow_populator.create_workflow( workflow )
        history_id = self.dataset_populator.new_history()
        hdca1 = self.dataset_collection_populator.create_list_in_history( history_id, contents=[("sample1-1", "1 2 3"), ("sample2-1", "7 8 9")] ).json()
        hdca2 = self.dataset_collection_populator.create_list_in_history( history_id, contents=[("sample1-2", "4 5 6"), ("sample2-2", "0 a b")] ).json()
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        label_map = { "list1": self._ds_entry( hdca1 ), "list2": self._ds_entry( hdca2 ) }
        workflow_request = dict(
            history="hist_id=%s" % history_id,
            workflow_id=workflow_id,
            ds_map=self._build_ds_map( workflow_id, label_map ),
        )
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        self.assertEquals("1 2 3\n4 5 6\n7 8 9\n0 a b\n", self.dataset_populator.get_history_dataset_content( history_id ) )

    def test_workflow_stability( self ):
        # Run this index stability test with following command:
        #   ./run_tests.sh test/api/test_workflows.py:WorkflowsApiTestCase.test_workflow_stability
        from pkg_resources import resource_string
        num_tests = 1
        for workflow_file in [ "test_workflow_topoambigouity.ga", "test_workflow_topoambigouity_auto_laidout.ga" ]:
            workflow_str = resource_string( __name__, workflow_file )
            workflow = self.workflow_populator.load_workflow( "test1", content=workflow_str )
            last_step_map = self._step_map( workflow )
            for i in range(num_tests):
                uploaded_workflow_id = self.workflow_populator.create_workflow( workflow )
                download_response = self._get( "workflows/%s/download" % uploaded_workflow_id )
                downloaded_workflow = download_response.json()
                step_map = self._step_map(downloaded_workflow)
                assert step_map == last_step_map
                last_step_map = step_map

    def _step_map(self, workflow):
        # Build dict mapping 'tep index to input name.
        step_map = {}
        for step_index, step in workflow["steps"].iteritems():
            if step[ "type" ] == "data_input":
                step_map[step_index] = step["inputs"][0]["name"]
        return step_map

    @skip_without_tool( "cat1" )
    def test_extract_from_history( self ):
        history_id = self.dataset_populator.new_history()
        # Run the simple test workflow and extract it back out from history
        cat1_job_id = self.__setup_and_run_cat1_workflow( history_id=history_id )
        contents_response = self._get( "histories/%s/contents" % history_id )
        input_hids = map( lambda c: c[ "hid" ], contents_response.json()[ 0:2 ] )
        downloaded_workflow = self._extract_and_download_workflow(
            from_history_id=history_id,
            dataset_ids=dumps( input_hids ),
            job_ids=dumps( [ cat1_job_id ] ),
            workflow_name="test import from history",
        )
        self.assertEquals( downloaded_workflow[ "name" ], "test import from history" )
        self.__assert_looks_like_cat1_example_workflow( downloaded_workflow )

    def test_extract_with_copied_inputs( self ):
        old_history_id = self.dataset_populator.new_history()
        # Run the simple test workflow and extract it back out from history
        self.__setup_and_run_cat1_workflow( history_id=old_history_id )

        history_id = self.dataset_populator.new_history()

        # Bug cannot mess up hids or these don't extract correctly. See Trello card here:
        # https://trello.com/c/mKzLbM2P
        # # create dummy dataset to complicate hid mapping
        # self.dataset_populator.new_dataset( history_id, content="dummydataset" )
        # offset = 1

        offset = 0
        old_contents = self._get( "histories/%s/contents" % old_history_id ).json()
        for old_dataset in old_contents:
            self.__copy_content_to_history( history_id, old_dataset )
        new_contents = self._get( "histories/%s/contents" % history_id ).json()
        input_hids = map( lambda c: c[ "hid" ], new_contents[ (offset + 0):(offset + 2) ] )
        cat1_job_id = self.__job_id( history_id, new_contents[ (offset + 2) ][ "id" ] )
        downloaded_workflow = self._extract_and_download_workflow(
            from_history_id=history_id,
            dataset_ids=dumps( input_hids ),
            job_ids=dumps( [ cat1_job_id ] ),
            workflow_name="test import from history",
        )
        self.__assert_looks_like_cat1_example_workflow( downloaded_workflow )

    def __assert_looks_like_cat1_example_workflow( self, downloaded_workflow ):
        assert len( downloaded_workflow[ "steps" ] ) == 3
        input_steps = self._get_steps_of_type( downloaded_workflow, "data_input", expected_len=2 )
        tool_step = self._get_steps_of_type( downloaded_workflow, "tool", expected_len=1 )[ 0 ]

        input1 = tool_step[ "input_connections" ][ "input1" ]
        input2 = tool_step[ "input_connections" ][ "queries_0|input2" ]

        self.assertEquals( input_steps[ 0 ][ "id" ], input1[ "id" ] )
        self.assertEquals( input_steps[ 1 ][ "id" ], input2[ "id" ] )

    def __setup_and_run_cat1_workflow( self, history_id ):
        workflow = self.workflow_populator.load_workflow( name="test_for_extract" )
        workflow_request, history_id = self._setup_workflow_run( workflow, history_id=history_id )
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )

        self.dataset_populator.wait_for_history( history_id, assert_ok=True, timeout=10 )
        return self.__cat_job_id( history_id )

    def __cat_job_id( self, history_id ):
        data = dict( history_id=history_id, tool_id="cat1" )
        jobs_response = self._get( "jobs", data=data )
        self._assert_status_code_is( jobs_response, 200 )
        cat1_job_id = jobs_response.json()[ 0 ][ "id" ]
        return cat1_job_id

    def __job_id( self, history_id, dataset_id ):
        url = "histories/%s/contents/%s/provenance" % ( history_id, dataset_id )
        prov_response = self._get( url, data=dict( follow=False ) )
        self._assert_status_code_is( prov_response, 200 )
        return prov_response.json()[ "job_id" ]

    @skip_without_tool( "collection_paired_test" )
    def test_extract_workflows_with_dataset_collections( self ):
        history_id = self.dataset_populator.new_history()
        hdca = self.dataset_collection_populator.create_pair_in_history( history_id ).json()
        hdca_id = hdca[ "id" ]
        inputs = {
            "f1": dict( src="hdca", id=hdca_id )
        }
        run_output = self.dataset_populator.run_tool(
            tool_id="collection_paired_test",
            inputs=inputs,
            history_id=history_id,
        )
        job_id = run_output[ "jobs" ][ 0 ][ "id" ]
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        downloaded_workflow = self._extract_and_download_workflow(
            from_history_id=history_id,
            dataset_collection_ids=dumps( [ hdca[ "hid" ] ] ),
            job_ids=dumps( [ job_id ] ),
            workflow_name="test import from history",
        )
        collection_steps = self._get_steps_of_type( downloaded_workflow, "data_collection_input", expected_len=1 )
        collection_step = collection_steps[ 0 ]
        collection_step_state = loads( collection_step[ "tool_state" ] )
        self.assertEquals( collection_step_state[ "collection_type" ], u"paired" )

    def test_empty_create( self ):
        response = self._post( "workflows" )
        self._assert_status_code_is( response, 400 )
        self._assert_error_code_is( response, error_codes.USER_REQUEST_MISSING_PARAMETER )

    def test_invalid_create_multiple_types( self ):
        data = {
            'shared_workflow_id': '1234567890abcdef',
            'from_history_id': '1234567890abcdef'
        }
        response = self._post( "workflows", data )
        self._assert_status_code_is( response, 400 )
        self._assert_error_code_is( response, error_codes.USER_REQUEST_INVALID_PARAMETER )

    @skip_without_tool( "random_lines1" )
    def test_extract_mapping_workflow_from_history( self ):
        history_id = self.dataset_populator.new_history()
        hdca, job_id1, job_id2 = self.__run_random_lines_mapped_over_pair( history_id )
        downloaded_workflow = self._extract_and_download_workflow(
            from_history_id=history_id,
            dataset_collection_ids=dumps( [ hdca[ "hid" ] ] ),
            job_ids=dumps( [ job_id1, job_id2 ] ),
            workflow_name="test import from mapping history",
        )
        self.__assert_looks_like_randomlines_mapping_workflow( downloaded_workflow )

    def test_extract_copied_mapping_from_history( self ):
        old_history_id = self.dataset_populator.new_history()
        hdca, job_id1, job_id2 = self.__run_random_lines_mapped_over_pair( old_history_id )

        history_id = self.dataset_populator.new_history()
        old_contents = self._get( "histories/%s/contents" % old_history_id ).json()
        for old_content in old_contents:
            self.__copy_content_to_history( history_id, old_content )
        # API test is somewhat contrived since there is no good way
        # to retrieve job_id1, job_id2 like this for copied dataset
        # collections I don't think.
        downloaded_workflow = self._extract_and_download_workflow(
            from_history_id=history_id,
            dataset_collection_ids=dumps( [ hdca[ "hid" ] ] ),
            job_ids=dumps( [ job_id1, job_id2 ] ),
            workflow_name="test import from history",
        )
        self.__assert_looks_like_randomlines_mapping_workflow( downloaded_workflow )

    @skip_without_tool( "random_lines1" )
    @skip_without_tool( "multi_data_param" )
    def test_extract_reduction_from_history( self ):
        history_id = self.dataset_populator.new_history()
        hdca = self.dataset_collection_populator.create_pair_in_history( history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"] ).json()
        hdca_id = hdca[ "id" ]
        inputs1 = {
            "input": { "batch": True, "values": [ { "src": "hdca", "id": hdca_id } ] },
            "num_lines": 2
        }
        implicit_hdca1, job_id1 = self._run_tool_get_collection_and_job_id( history_id, "random_lines1", inputs1 )
        inputs2 = {
            "f1": { "src": "hdca", "id": implicit_hdca1[ "id" ] },
            "f2": { "src": "hdca", "id": implicit_hdca1[ "id" ] },
        }
        reduction_run_output = self.dataset_populator.run_tool(
            tool_id="multi_data_param",
            inputs=inputs2,
            history_id=history_id,
        )
        job_id2 = reduction_run_output[ "jobs" ][ 0 ][ "id" ]
        self.dataset_populator.wait_for_history( history_id, assert_ok=True, timeout=20 )
        downloaded_workflow = self._extract_and_download_workflow(
            from_history_id=history_id,
            dataset_collection_ids=dumps( [ hdca[ "hid" ] ] ),
            job_ids=dumps( [ job_id1, job_id2 ] ),
            workflow_name="test import reduction",
        )
        assert len( downloaded_workflow[ "steps" ] ) == 3
        collect_step_idx = self._assert_first_step_is_paired_input( downloaded_workflow )
        tool_steps = self._get_steps_of_type( downloaded_workflow, "tool", expected_len=2 )
        random_lines_map_step = tool_steps[ 0 ]
        reduction_step = tool_steps[ 1 ]
        random_lines_input = random_lines_map_step[ "input_connections" ][ "input" ]
        assert random_lines_input[ "id" ] == collect_step_idx
        reduction_step_input = reduction_step[ "input_connections" ][ "f1" ]
        assert reduction_step_input[ "id"] == random_lines_map_step[ "id" ]

    def __copy_content_to_history( self, history_id, content ):
        if content[ "history_content_type" ] == "dataset":
            payload = dict(
                source="hda",
                content=content["id"]
            )
            response = self._post( "histories/%s/contents/datasets" % history_id, payload )

        else:
            payload = dict(
                source="hdca",
                content=content["id"]
            )
            response = self._post( "histories/%s/contents/dataset_collections" % history_id, payload )
        self._assert_status_code_is( response, 200 )
        return response.json()

    def __run_random_lines_mapped_over_pair( self, history_id ):
        hdca = self.dataset_collection_populator.create_pair_in_history( history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"] ).json()
        hdca_id = hdca[ "id" ]
        inputs1 = {
            "input": { "batch": True, "values": [ { "src": "hdca", "id": hdca_id } ] },
            "num_lines": 2
        }
        implicit_hdca1, job_id1 = self._run_tool_get_collection_and_job_id( history_id, "random_lines1", inputs1 )
        inputs2 = {
            "input": { "batch": True, "values": [ { "src": "hdca", "id": implicit_hdca1[ "id" ] } ] },
            "num_lines": 1
        }
        _, job_id2 = self._run_tool_get_collection_and_job_id( history_id, "random_lines1", inputs2 )
        return hdca, job_id1, job_id2

    def __assert_looks_like_randomlines_mapping_workflow( self, downloaded_workflow ):
        # Assert workflow is input connected to a tool step with one output
        # connected to another tool step.
        assert len( downloaded_workflow[ "steps" ] ) == 3
        collect_step_idx = self._assert_first_step_is_paired_input( downloaded_workflow )
        tool_steps = self._get_steps_of_type( downloaded_workflow, "tool", expected_len=2 )
        tool_step_idxs = []
        tool_input_step_idxs = []
        for tool_step in tool_steps:
            self._assert_has_key( tool_step[ "input_connections" ], "input" )
            input_step_idx = tool_step[ "input_connections" ][ "input" ][ "id" ]
            tool_step_idxs.append( tool_step[ "id" ] )
            tool_input_step_idxs.append( input_step_idx )

        assert collect_step_idx not in tool_step_idxs
        assert tool_input_step_idxs[ 0 ] == collect_step_idx
        assert tool_input_step_idxs[ 1 ] == tool_step_idxs[ 0 ]

    def _run_tool_get_collection_and_job_id( self, history_id, tool_id, inputs ):
        run_output1 = self.dataset_populator.run_tool(
            tool_id=tool_id,
            inputs=inputs,
            history_id=history_id,
        )
        implicit_hdca = run_output1[ "implicit_collections" ][ 0 ]
        job_id = run_output1[ "jobs" ][ 0 ][ "id" ]
        self.dataset_populator.wait_for_history( history_id, assert_ok=True, timeout=20 )
        return implicit_hdca, job_id

    def _assert_first_step_is_paired_input( self, downloaded_workflow ):
        collection_steps = self._get_steps_of_type( downloaded_workflow, "data_collection_input", expected_len=1 )
        collection_step = collection_steps[ 0 ]
        collection_step_state = loads( collection_step[ "tool_state" ] )
        self.assertEquals( collection_step_state[ "collection_type" ], u"paired" )
        collect_step_idx = collection_step[ "id" ]
        return collect_step_idx

    def _extract_and_download_workflow( self, **extract_payload ):
        create_workflow_response = self._post( "workflows", data=extract_payload )
        self._assert_status_code_is( create_workflow_response, 200 )

        new_workflow_id = create_workflow_response.json()[ "id" ]
        download_response = self._get( "workflows/%s/download" % new_workflow_id )
        self._assert_status_code_is( download_response, 200 )
        downloaded_workflow = download_response.json()
        return downloaded_workflow

    def _get_steps_of_type( self, downloaded_workflow, type, expected_len=None ):
        steps = [ s for s in downloaded_workflow[ "steps" ].values() if s[ "type" ] == type ]
        if expected_len is not None:
            n = len( steps )
            assert n == expected_len, "Expected %d steps of type %s, found %d" % ( expected_len, type, n )
        return sorted( steps, key=operator.itemgetter("id") )

    @skip_without_tool( "cat1" )
    def test_run_with_pja( self ):
        workflow = self.workflow_populator.load_workflow( name="test_for_pja_run", add_pja=True )
        workflow_request, history_id = self._setup_workflow_run( workflow, inputs_by='step_index' )
        workflow_request[ "replacement_params" ] = dumps( dict( replaceme="was replaced" ) )
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )
        content = self.dataset_populator.get_history_dataset_details( history_id, wait=True, assert_ok=True )
        assert content[ "name" ] == "foo was replaced"

    @skip_without_tool( "random_lines1" )
    def test_run_replace_params_by_tool( self ):
        workflow_request, history_id = self._setup_random_x2_workflow( "test_for_replace_tool_params" )
        workflow_request[ "parameters" ] = dumps( dict( random_lines1=dict( num_lines=5 ) ) )
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        # Would be 8 and 6 without modification
        self.__assert_lines_hid_line_count_is( history_id, 2, 5 )
        self.__assert_lines_hid_line_count_is( history_id, 3, 5 )

    @skip_without_tool( "validation_default" )
    def test_parameter_substitution_validation( self ):
        substitions = dict( input1="\" ; echo \"moo" )
        run_workflow_response, history_id = self._run_validation_workflow_with_substitions( substitions )

        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        self.assertEquals("__dq__ X echo __dq__moo\n", self.dataset_populator.get_history_dataset_content( history_id, hid=1 ) )

    @skip_without_tool( "validation_default" )
    def test_parameter_substitution_validation_value_errors_1( self ):
        substitions = dict( select_param="\" ; echo \"moo" )
        run_workflow_response, history_id = self._run_validation_workflow_with_substitions( substitions )

        self._assert_status_code_is( run_workflow_response, 400 )

    def _run_validation_workflow_with_substitions( self, substitions ):
        workflow = self.workflow_populator.load_workflow_from_resource( "test_workflow_validation_1" )
        uploaded_workflow_id = self.workflow_populator.create_workflow( workflow )
        history_id = self.dataset_populator.new_history()
        workflow_request = dict(
            history="hist_id=%s" % history_id,
            workflow_id=uploaded_workflow_id,
            parameters=dumps( dict( validation_default=substitions ) )
        )
        run_workflow_response = self._post( "workflows", data=workflow_request )
        return run_workflow_response, history_id

    @skip_without_tool( "random_lines1" )
    def test_run_replace_params_by_steps( self ):
        workflow_request, history_id = self._setup_random_x2_workflow( "test_for_replace_step_params" )
        workflow_summary_response = self._get( "workflows/%s" % workflow_request[ "workflow_id" ] )
        self._assert_status_code_is( workflow_summary_response, 200 )
        steps = workflow_summary_response.json()[ "steps" ]
        last_step_id = str( max( map( int, steps.keys() ) ) )
        params = dumps( { last_step_id: dict( num_lines=5 ) } )
        workflow_request[ "parameters" ] = params
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        # Would be 8 and 6 without modification
        self.__assert_lines_hid_line_count_is( history_id, 2, 8 )
        self.__assert_lines_hid_line_count_is( history_id, 3, 5 )

    def test_pja_import_export( self ):
        workflow = self.workflow_populator.load_workflow( name="test_for_pja_import", add_pja=True )
        uploaded_workflow_id = self.workflow_populator.create_workflow( workflow )
        download_response = self._get( "workflows/%s/download" % uploaded_workflow_id )
        downloaded_workflow = download_response.json()
        self._assert_has_keys( downloaded_workflow[ "steps" ], "0", "1", "2" )
        pjas = downloaded_workflow[ "steps" ][ "2" ][ "post_job_actions" ].values()
        assert len( pjas ) == 1, len( pjas )
        pja = pjas[ 0 ]
        self._assert_has_keys( pja, "action_type", "output_name", "action_arguments" )

    @skip_without_tool( "cat1" )
    def test_only_own_invocations_accessible( self ):
        workflow_id, usage = self._run_workflow_once_get_invocation( "test_usage")
        with self._different_user():
            usage_details_response = self._get( "workflows/%s/usage/%s" % ( workflow_id, usage[ "id" ] ) )
            self._assert_status_code_is( usage_details_response, 403 )

    @skip_without_tool( "cat1" )
    def test_invocation_usage( self ):
        workflow_id, usage = self._run_workflow_once_get_invocation( "test_usage")
        usage_details = self._invocation_details( workflow_id, usage[ "id" ] )
        # Assert some high-level things about the structure of data returned.
        self._assert_has_keys( usage_details, "inputs", "steps" )
        for step in usage_details[ "steps" ]:
            self._assert_has_keys( step, "workflow_step_id", "order_index", "id" )

    def _invocation_details( self, workflow_id, invocation_id ):
        invocation_details_response = self._get( "workflows/%s/usage/%s" % ( workflow_id, invocation_id ) )
        self._assert_status_code_is( invocation_details_response, 200 )
        invocation_details = invocation_details_response.json()
        return invocation_details

    def _run_workflow_once_get_invocation( self, name ):
        workflow = self.workflow_populator.load_workflow( name=name )
        workflow_request, history_id = self._setup_workflow_run( workflow )
        workflow_id = workflow_request[ "workflow_id" ]
        response = self._get( "workflows/%s/usage" % workflow_id )
        self._assert_status_code_is( response, 200 )
        assert len( response.json() ) == 0
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )

        response = self._get( "workflows/%s/usage" % workflow_id )
        self._assert_status_code_is( response, 200 )
        usages = response.json()
        assert len( usages ) == 1
        return workflow_id, usages[ 0 ]

    def _setup_workflow_run( self, workflow, inputs_by='step_id', history_id=None ):
        uploaded_workflow_id = self.workflow_populator.create_workflow( workflow )
        if not history_id:
            history_id = self.dataset_populator.new_history()
        hda1 = self.dataset_populator.new_dataset( history_id, content="1 2 3" )
        hda2 = self.dataset_populator.new_dataset( history_id, content="4 5 6" )
        workflow_request = dict(
            history="hist_id=%s" % history_id,
            workflow_id=uploaded_workflow_id,
        )
        label_map = {
            'WorkflowInput1': self._ds_entry(hda1),
            'WorkflowInput2': self._ds_entry(hda2)
        }
        if inputs_by == 'step_id':
            ds_map = self._build_ds_map( uploaded_workflow_id, label_map )
            workflow_request[ "ds_map" ] = ds_map
        elif inputs_by == "step_index":
            index_map = {
                '0': self._ds_entry(hda1),
                '1': self._ds_entry(hda2)
            }
            workflow_request[ "inputs" ] = dumps( index_map )
            workflow_request[ "inputs_by" ] = 'step_index'
        elif inputs_by == "name":
            workflow_request[ "inputs" ] = dumps( label_map )
            workflow_request[ "inputs_by" ] = 'name'

        return workflow_request, history_id

    def _build_ds_map( self, workflow_id, label_map ):
        workflow_inputs = self._workflow_inputs( workflow_id )
        ds_map = {}
        for key, value in workflow_inputs.iteritems():
            label = value[ "label" ]
            if label in label_map:
                ds_map[ key ] = label_map[ label ]
        return dumps( ds_map )

    def _setup_random_x2_workflow( self, name ):
        workflow = self.workflow_populator.load_random_x2_workflow( name )
        uploaded_workflow_id = self.workflow_populator.create_workflow( workflow )
        workflow_inputs = self._workflow_inputs( uploaded_workflow_id )
        key = workflow_inputs.keys()[ 0 ]
        history_id = self.dataset_populator.new_history()
        ten_lines = "\n".join( map( str, range( 10 ) ) )
        hda1 = self.dataset_populator.new_dataset( history_id, content=ten_lines )
        workflow_request = dict(
            history="hist_id=%s" % history_id,
            workflow_id=uploaded_workflow_id,
            ds_map=dumps( {
                key: self._ds_entry(hda1),
            } ),
        )
        return workflow_request, history_id

    def _workflow_inputs( self, uploaded_workflow_id ):
        workflow_show_resposne = self._get( "workflows/%s" % uploaded_workflow_id )
        self._assert_status_code_is( workflow_show_resposne, 200 )
        workflow_inputs = workflow_show_resposne.json()[ "inputs" ]
        return workflow_inputs

    def _ds_entry( self, hda ):
        src = 'hda'
        if 'history_content_type' in hda and hda[ 'history_content_type' ] == "dataset_collection":
            src = 'hdca'
        return dict( src=src, id=hda[ "id" ] )

    def _assert_user_has_workflow_with_name( self, name ):
        names = self.__workflow_names()
        assert name in names, "No workflows with name %s in users workflows <%s>" % ( name, names )

    def __assert_lines_hid_line_count_is( self, history, hid, lines ):
        contents_url = "histories/%s/contents" % history
        history_contents_response = self._get( contents_url )
        self._assert_status_code_is( history_contents_response, 200 )
        hda_summary = filter( lambda hc: hc[ "hid" ] == hid, history_contents_response.json() )[ 0 ]
        hda_info_response = self._get( "%s/%s" % ( contents_url, hda_summary[ "id" ] ) )
        self._assert_status_code_is( hda_info_response, 200 )
        self.assertEquals( hda_info_response.json()[ "metadata_data_lines" ], lines )

    def __workflow_names( self ):
        index_response = self._get( "workflows" )
        self._assert_status_code_is( index_response, 200 )
        names = map( lambda w: w[ "name" ], index_response.json() )
        return names

    def __import_workflow( self, workflow_id, deprecated_route=False ):
        if deprecated_route:
            route = "workflows/import"
            import_data = dict(
                workflow_id=workflow_id,
            )
        else:
            route = "workflows"
            import_data = dict(
                shared_workflow_id=workflow_id,
            )
        return self._post( route, import_data )
