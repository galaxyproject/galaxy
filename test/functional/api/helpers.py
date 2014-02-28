import time
import json
import StringIO
from pkg_resources import resource_string

# Simple workflow that takes an input and call cat wrapper on it.
workflow_str = resource_string( __name__, "test_workflow_1.ga" )
# Simple workflow that takes an input and filters with random lines twice in a
# row - first grabbing 8 lines at random and then 6.
workflow_random_x2_str = resource_string( __name__, "test_workflow_2.ga" )


# TODO: Rework this so it is a stand-alone object like workflow
# populator below instead of mixin.
class TestsDatasets:

    def _new_dataset( self, history_id, content='TestData123', **kwds ):
        payload = self._upload_payload( history_id, content, **kwds )
        run_response = self._post( "tools", data=payload )
        self._assert_status_code_is( run_response, 200 )
        return run_response.json()["outputs"][0]

    def _wait_for_history( self, history_id, assert_ok=False ):
        wait_on_state( lambda: self._get( "histories/%s" % history_id ), assert_ok=assert_ok )

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
            inputs=json.dumps(inputs),
            history_id=history_id,
            **kwds
        )


class WorkflowPopulator( object ):
    # Impulse is to make this a Mixin, but probably better as an object.

    def __init__( self, api_test_case ):
        self.api_test_case = api_test_case

    def load_workflow( self, name, content=workflow_str, add_pja=False ):
        workflow = json.loads( content )
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
            workflow=json.dumps( workflow ),
            **create_kwds
        )
        upload_response = self.api_test_case._post( "workflows/upload", data=data )
        uploaded_workflow_id = upload_response.json()[ "id" ]
        return uploaded_workflow_id


class LibraryPopulator( object ):

    def __init__( self, api_test_case ):
        self.api_test_case = api_test_case
        self.galaxy_interactor = api_test_case.galaxy_interactor

    def new_private_library( self, name ):
        library = self.new_library( name )
        library_id = library[ "id" ]

        role_id = self.user_private_role_id()
        self.set_permissions( library_id, role_id )
        return library

    def new_library( self, name ):
        data = dict( name=name )
        create_response = self.galaxy_interactor.post( "libraries", data=data, admin=True )
        return create_response.json()

    def set_permissions( self, library_id, role_id=None ):
        if role_id:
            perm_list = json.dumps( role_id )
        else:
            perm_list = json.dumps( [] )

        permissions = dict(
            LIBRARY_ACCESS_in=perm_list,
            LIBRARY_MODIFY_in=perm_list,
            LIBRARY_ADD_in=perm_list,
            LIBRARY_MANAGE_in=perm_list,
        )
        self.galaxy_interactor.post( "libraries/%s/permissions" % library_id, data=permissions, admin=True )

    def user_email( self ):
        users_response = self.galaxy_interactor.get( "users" )
        users = users_response.json()
        assert len( users ) == 1
        return users[ 0 ][ "email" ]

    def user_private_role_id( self ):
        user_email = self.user_email()
        roles_response = self.api_test_case.galaxy_interactor.get( "roles", admin=True )
        users_roles = [ r for r in roles_response.json() if r[ "name" ] == user_email ]
        assert len( users_roles ) == 1
        return users_roles[ 0 ][ "id" ]

    def create_dataset_request( self, library, **kwds ):
        create_data = {
            "folder_id": kwds.get( "folder_id", library[ "root_folder_id" ] ),
            "create_type": "file",
            "files_0|NAME": kwds.get( "name", "NewFile" ),
            "upload_option": kwds.get( "upload_option", "upload_file" ),
            "file_type": kwds.get( "file_type", "auto" ),
            "db_key": kwds.get( "db_key", "?" ),
        }
        files = {
            "files_0|file_data": kwds.get( "file", StringIO.StringIO( kwds.get( "contents", "TestData" ) ) ),
        }
        return create_data, files

    def new_library_dataset( self, name, **create_dataset_kwds ):
        library = self.new_private_library( name )
        payload, files = self.create_dataset_request( library, **create_dataset_kwds )
        url_rel = "libraries/%s/contents" % ( library[ "id" ] )
        dataset = self.api_test_case.galaxy_interactor.post( url_rel, payload, files=files ).json()[0]

        def show():
            return self.api_test_case.galaxy_interactor.get( "libraries/%s/contents/%s" % ( library[ "id" ], dataset[ "id" ] ) )

        wait_on_state(show)
        return show().json()


def wait_on_state( state_func, assert_ok=False, timeout=5 ):
    delta = .1
    iteration = 0
    while True:
        if (delta * iteration) > timeout:
            assert False, "Timed out waiting on state."
        iteration += 1
        response = state_func()
        assert response.status_code == 200, "Failed to fetch state update while waiting."
        state = response.json()[ "state" ]
        if state not in [ "running", "queued", "new" ]:
            break
        time.sleep( delta )
    if assert_ok:
        assert state == "ok", "Final state - %s - not okay." % state
