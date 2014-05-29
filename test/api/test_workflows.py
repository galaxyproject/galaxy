from base import api
from json import dumps
from json import loads
import operator
import time
from .helpers import WorkflowPopulator
from .helpers import DatasetPopulator
from .helpers import DatasetCollectionPopulator
from .helpers import skip_without_tool

from base.interactor import delete_request  # requests like delete


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

    def test_delete( self ):
        workflow_id = self.workflow_populator.simple_workflow( "test_delete" )
        workflow_name = "test_delete (imported from API)"
        self._assert_user_has_workflow_with_name( workflow_name )
        workflow_url = self._api_url( "workflows/%s" % workflow_id, use_key=True )
        delete_response = delete_request( workflow_url )
        self._assert_status_code_is( delete_response, 200 )
        # Make sure workflow is no longer in index by default.
        assert workflow_name not in self.__workflow_names()

    def test_other_cannot_delete( self ):
        workflow_id = self.workflow_populator.simple_workflow( "test_other_delete" )
        with self._different_user():
            workflow_url = self._api_url( "workflows/%s" % workflow_id, use_key=True )
            delete_response = delete_request( workflow_url )
            self._assert_status_code_is( delete_response, 403 )

    def test_index( self ):
        index_response = self._get( "workflows" )
        self._assert_status_code_is( index_response, 200 )
        assert isinstance( index_response.json(), list )

    def test_import( self ):
        data = dict(
            workflow=dumps( self.workflow_populator.load_workflow( name="test_import" ) ),
        )
        upload_response = self._post( "workflows/upload", data=data )
        self._assert_status_code_is( upload_response, 200 )
        self._assert_user_has_workflow_with_name( "test_import (imported from API)" )

    def test_export( self ):
        uploaded_workflow_id = self.workflow_populator.simple_workflow( "test_for_export" )
        download_response = self._get( "workflows/%s/download" % uploaded_workflow_id )
        self._assert_status_code_is( download_response, 200 )
        downloaded_workflow = download_response.json()
        assert downloaded_workflow[ "name" ] == "test_for_export (imported from API)"
        assert len( downloaded_workflow[ "steps" ] ) == 3
        first_input = downloaded_workflow[ "steps" ][ "0" ][ "inputs" ][ 0 ]
        assert first_input[ "name" ] == "WorkflowInput1"

    @skip_without_tool( "cat1" )
    def test_run_workflow( self ):
        workflow = self.workflow_populator.load_workflow( name="test_for_run" )
        workflow_request, history_id = self._setup_workflow_run( workflow )
        # TODO: This should really be a post to workflows/<workflow_id>/run or
        # something like that.
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )

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

        print downloaded_workflow
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
            "input|__collection_multirun__": hdca_id,
            "num_lines": 2
        }
        implicit_hdca1, job_id1 = self._run_tool_get_collection_and_job_id( history_id, "random_lines1", inputs1 )
        inputs2 = {
            "f1": "__collection_reduce__|%s" % ( implicit_hdca1[ "id" ] ),
            "f2": "__collection_reduce__|%s" % ( implicit_hdca1[ "id" ] )
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
            "input|__collection_multirun__": hdca_id,
            "num_lines": 2
        }
        implicit_hdca1, job_id1 = self._run_tool_get_collection_and_job_id( history_id, "random_lines1", inputs1 )
        inputs2 = {
            "input|__collection_multirun__": implicit_hdca1[ "id" ],
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
    def test_invocation_usage( self ):
        workflow = self.workflow_populator.load_workflow( name="test_usage" )
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

        usage_details_response = self._get( "workflows/%s/usage/%s" % ( workflow_id, usages[ 0 ][ "id" ] ) )
        self._assert_status_code_is( usage_details_response, 200 )
        usage_details = usage_details_response.json()
        # Assert some high-level things about the structure of data returned.
        self._assert_has_keys( usage_details, "inputs", "steps" )
        for step in usage_details[ "steps" ].values():
            self._assert_has_keys( step, "workflow_step_id", "order_index" )

    @skip_without_tool( "cat1" )
    def test_post_job_action( self ):
        """ Tests both import and execution of post job actions.
        """
        workflow = self.workflow_populator.load_workflow( name="test_for_pja_run", add_pja=True )
        workflow_request, history_id = self._setup_workflow_run( workflow )
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        time.sleep(.1)  # Give another little bit of time for rename (needed?)
        contents = self._get( "histories/%s/contents" % history_id ).json()
        # loading workflow with add_pja=True causes workflow output to be
        # renamed to 'the_new_name'.
        assert "the_new_name" in map( lambda hda: hda[ "name" ], contents )

    def _setup_workflow_run( self, workflow, history_id=None ):
        uploaded_workflow_id = self.workflow_populator.create_workflow( workflow )
        workflow_inputs = self._workflow_inputs( uploaded_workflow_id )
        step_1 = step_2 = None
        for key, value in workflow_inputs.iteritems():
            label = value[ "label" ]
            if label == "WorkflowInput1":
                step_1 = key
            if label == "WorkflowInput2":
                step_2 = key
        if not history_id:
            history_id = self.dataset_populator.new_history()
        hda1 = self.dataset_populator.new_dataset( history_id, content="1 2 3" )
        hda2 = self.dataset_populator.new_dataset( history_id, content="4 5 6" )
        workflow_request = dict(
            history="hist_id=%s" % history_id,
            workflow_id=uploaded_workflow_id,
            ds_map=dumps( {
                step_1: self._ds_entry(hda1),
                step_2: self._ds_entry(hda2),
            } ),
        )
        return workflow_request, history_id

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
        return dict( src="hda", id=hda[ "id" ] )

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
