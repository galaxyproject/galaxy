import time
from json import dumps
from json import loads
from pkg_resources import resource_string

# Simple workflow that takes an input and call cat wrapper on it.
workflow_str = resource_string( __name__, "test_workflow_1.ga" )
# Simple workflow that takes an input and filters with random lines twice in a
# row - first grabbing 8 lines at random and then 6.
workflow_random_x2_str = resource_string( __name__, "test_workflow_2.ga" )


class TestsDatasets:

    def _new_dataset( self, history_id, content='TestData123', **kwds ):
        payload = self._upload_payload( history_id, content, **kwds )
        run_response = self._post( "tools", data=payload )
        self._assert_status_code_is( run_response, 200 )
        return run_response.json()["outputs"][0]

    def _wait_for_history( self, history_id, assert_ok=False ):
        while True:
            history_details_response = self._get( "histories/%s" % history_id )
            self._assert_status_code_is( history_details_response, 200 )
            history_state = history_details_response.json()[ "state" ]
            if history_state not in [ "running", "queued" ]:
                break
            time.sleep( .1 )
        if assert_ok:
            self.assertEquals( history_state, 'ok' )

    def _new_history( self, **kwds ):
        name = kwds.get( "name", "API Test History" )
        create_history_response = self._post( "histories", data=dict( name=name ) )
        self._assert_status_code_is( create_history_response, 200 )
        history_id = create_history_response.json()[ "id" ]
        return history_id

    def _upload_payload( self, history_id, content, **kwds ):
        name = kwds.get( "name", "Test Dataset" )
        dbkey = kwds.get( "dbkey", "?" )
        file_type = kwds.get( "file_type", 'txt' )
        upload_params = {
            'files_0|NAME': name,
            'files_0|url_paste': content,
            'dbkey': dbkey,
            'file_type': file_type,
        }
        if "to_posix_lines" in kwds:
            upload_params[ "files_0|to_posix_lines"] = kwds[ "to_posix_lines" ]
        if "space_to_tab" in kwds:
            upload_params[ "files_0|space_to_tab" ] = kwds[ "space_to_tab" ]
        return self._run_tool_payload(
            tool_id='upload1',
            inputs=upload_params,
            history_id=history_id,
            upload_type='upload_dataset'
        )

    def _run_tool_payload( self, tool_id, inputs, history_id, **kwds ):
        return dict(
            tool_id=tool_id,
            inputs=dumps(inputs),
            history_id=history_id,
            **kwds
        )


class WorkflowPopulator( object ):
    # Impulse is to make this a Mixin, but probably better as an object.

    def __init__( self, api_test_case ):
        self.api_test_case = api_test_case

    def load_workflow( self, name, content=workflow_str, add_pja=False ):
        workflow = loads( content )
        workflow[ "name" ] = name
        if add_pja:
            tool_step = workflow[ "steps" ][ "2" ]
            tool_step[ "post_job_actions" ][ "RenameDatasetActionout_file1" ] = dict(
                action_type="RenameDatasetAction",
                output_name="out_file1",
                action_arguments=dict( newname="the_new_name" ),
            )
        return workflow

    def load_random_x2_workflow( self, name ):
        return self.load_workflow( name, content=workflow_random_x2_str )

    def simple_workflow( self, name, **create_kwds ):
        workflow = self.load_workflow( name )
        return self.create_workflow( workflow, **create_kwds )

    def create_workflow( self, workflow, **create_kwds ):
        data = dict(
            workflow=dumps( workflow ),
            **create_kwds
        )
        upload_response = self.api_test_case._post( "workflows/upload", data=data )
        uploaded_workflow_id = upload_response.json()[ "id" ]
        return uploaded_workflow_id
