from base import api
from json import dumps
import time
from .helpers import WorkflowPopulator
from .helpers import DatasetPopulator

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

    def test_run_workflow( self ):
        workflow = self.workflow_populator.load_workflow( name="test_for_run" )
        workflow_request, history_id = self._setup_workflow_run( workflow )
        # TODO: This should really be a post to workflows/<workflow_id>/run or
        # something like that.
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )

    def test_extract_from_history( self ):
        workflow = self.workflow_populator.load_workflow( name="test_for_extract" )
        workflow_request, history_id = self._setup_workflow_run( workflow )
        contents_response = self._get( "histories/%s/contents" % history_id )
        self._assert_status_code_is( contents_response, 200 )
        hda_ids = map( lambda c: c[ "hid" ], contents_response.json() )

        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )

        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        data = dict( history_id=history_id, tool_id="cat1" )
        jobs_response = self._get( "jobs", data=data )
        self._assert_status_code_is( jobs_response, 200 )
        cat1_job_id = jobs_response.json()[ 0 ][ "id" ]

        contents_response = self._get( "history/%s/contents", data=data )
        create_from_data = dict(
            from_history_id=history_id,
            dataset_ids=dumps( hda_ids ),
            job_ids=dumps( [ cat1_job_id ] ),
            workflow_name="test import from history",
        )
        run_workflow_response = self._post( "workflows", data=create_from_data )
        self._assert_status_code_is( run_workflow_response, 200 )

        new_workflow_id = run_workflow_response.json()[ "id" ]
        download_response = self._get( "workflows/%s/download" % new_workflow_id )
        self._assert_status_code_is( download_response, 200 )
        downloaded_workflow = download_response.json()
        self.assertEquals( downloaded_workflow[ "name" ], "test import from history" )
        assert len( downloaded_workflow[ "steps" ] ) == 3

    def test_run_replace_params_by_tool( self ):
        workflow_request, history_id = self._setup_random_x2_workflow( "test_for_replace_tool_params" )
        workflow_request[ "parameters" ] = dumps( dict( random_lines1=dict( num_lines=5 ) ) )
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        # Would be 8 and 6 without modification
        self.__assert_lines_hid_line_count_is( history_id, 2, 5 )
        self.__assert_lines_hid_line_count_is( history_id, 3, 5 )

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

    def _setup_workflow_run( self, workflow ):
        uploaded_workflow_id = self.workflow_populator.create_workflow( workflow )
        workflow_inputs = self._workflow_inputs( uploaded_workflow_id )
        step_1 = step_2 = None
        for key, value in workflow_inputs.iteritems():
            label = value[ "label" ]
            if label == "WorkflowInput1":
                step_1 = key
            if label == "WorkflowInput2":
                step_2 = key
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
