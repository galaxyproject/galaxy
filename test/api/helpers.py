from base import api_asserts
from operator import itemgetter

import time
import json
import StringIO
from pkg_resources import resource_string

# Simple workflow that takes an input and call cat wrapper on it.
workflow_str = resource_string( __name__, "test_workflow_1.ga" )
# Simple workflow that takes an input and filters with random lines twice in a
# row - first grabbing 8 lines at random and then 6.
workflow_random_x2_str = resource_string( __name__, "test_workflow_2.ga" )


DEFAULT_HISTORY_TIMEOUT = 10  # Secs to wait on history to turn ok


def skip_without_tool( tool_id ):
    """ Decorate an API test method as requiring a specific tool,
    have nose skip the test case is the tool is unavailable.
    """

    def method_wrapper( method ):

        def get_tool_ids( api_test_case ):
            index = api_test_case.galaxy_interactor.get( "tools", data=dict(in_panel=False) )
            tools = index.json()
            # In panels by default, so flatten out sections...
            tool_ids = map( itemgetter( "id" ), tools )
            return tool_ids

        def wrapped_method( api_test_case, *args, **kwargs ):
            if tool_id not in get_tool_ids( api_test_case ):
                from nose.plugins.skip import SkipTest
                raise SkipTest( )

            return method( api_test_case, *args, **kwargs )

        # Must preserve method name so nose can detect and report tests by
        # name.
        wrapped_method.__name__ = method.__name__
        return wrapped_method

    return method_wrapper


# Deprecated mixin, use dataset populator instead.
# TODO: Rework existing tests to target DatasetPopulator in a setup method instead.
class TestsDatasets:

    def _new_dataset( self, history_id, content='TestData123', **kwds ):
        return DatasetPopulator( self.galaxy_interactor ).new_dataset( history_id, content=content, **kwds)

    def _wait_for_history( self, history_id, assert_ok=False ):
        return DatasetPopulator( self.galaxy_interactor ).wait_for_history( history_id, assert_ok=assert_ok )

    def _new_history( self, **kwds ):
        return DatasetPopulator( self.galaxy_interactor ).new_history( **kwds )

    def _upload_payload( self, history_id, content, **kwds ):
        return DatasetPopulator( self.galaxy_interactor ).upload_payload( history_id, content, **kwds )

    def _run_tool_payload( self, tool_id, inputs, history_id, **kwds ):
        return DatasetPopulator( self.galaxy_interactor ).run_tool_payload( tool_id, inputs, history_id, **kwds )


class DatasetPopulator( object ):

    def __init__( self, galaxy_interactor ):
        self.galaxy_interactor = galaxy_interactor

    def new_dataset( self, history_id, content='TestData123', **kwds ):
        payload = self.upload_payload( history_id, content, **kwds )
        run_response = self.galaxy_interactor.post( "tools", data=payload )
        return run_response.json()["outputs"][0]

    def wait_for_history( self, history_id, assert_ok=False, timeout=DEFAULT_HISTORY_TIMEOUT ):
        wait_on_state( lambda: self.galaxy_interactor.get( "histories/%s" % history_id ), assert_ok=assert_ok, timeout=timeout )

    def new_history( self, **kwds ):
        name = kwds.get( "name", "API Test History" )
        create_history_response = self.galaxy_interactor.post( "histories", data=dict( name=name ) )
        history_id = create_history_response.json()[ "id" ]
        return history_id

    def upload_payload( self, history_id, content, **kwds ):
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
        return self.run_tool_payload(
            tool_id='upload1',
            inputs=upload_params,
            history_id=history_id,
            upload_type='upload_dataset'
        )

    def run_tool_payload( self, tool_id, inputs, history_id, **kwds ):
        return dict(
            tool_id=tool_id,
            inputs=json.dumps(inputs),
            history_id=history_id,
            **kwds
        )

    def run_tool( self, tool_id, inputs, history_id, **kwds ):
        payload = self.run_tool_payload( tool_id, inputs, history_id, **kwds )
        tool_response = self.galaxy_interactor.post( "tools", data=payload )
        api_asserts.assert_status_code_is( tool_response, 200 )
        return tool_response.json()

    def get_history_dataset_content( self, history_id, wait=True, **kwds ):
        dataset_id = self.__history_dataset_id( history_id, wait=wait, **kwds )
        display_response = self.__get_contents_request( history_id, "/%s/display" % dataset_id )
        assert display_response.status_code == 200, display_response.content
        return display_response.content

    def get_history_dataset_details( self, history_id, **kwds ):
        dataset_id = self.__history_dataset_id( history_id, **kwds )
        details_response = self.__get_contents_request( history_id, "/%s" % dataset_id )
        assert details_response.status_code == 200
        return details_response.json()

    def __history_dataset_id( self, history_id, wait=True, **kwds ):
        if wait:
            assert_ok = kwds.get( "assert_ok", True )
            self.wait_for_history( history_id, assert_ok=assert_ok )
        # kwds should contain a 'dataset' object response, a 'dataset_id' or
        # the last dataset in the history will be fetched.
        if "dataset_id" in kwds:
            dataset_id = kwds[ "dataset_id" ]
        elif "dataset" in kwds:
            dataset_id = kwds[ "dataset" ][ "id" ]
        else:
            hid = kwds.get( "hid", None )  # If not hid, just grab last dataset
            if hid:
                index = hid - 1
            else:
                # No hid specified - just grab most recent element.
                index = -1
            dataset_contents = self.__get_contents_request( history_id ).json()
            dataset_id = dataset_contents[ index ][ "id" ]
        return dataset_id

    def __get_contents_request( self, history_id, suffix=""):
        url = "histories/%s/contents" % history_id
        if suffix:
            url = "%s%s" % ( url, suffix )
        return self.galaxy_interactor.get( url )


class WorkflowPopulator( object ):
    # Impulse is to make this a Mixin, but probably better as an object.

    def __init__( self, galaxy_interactor ):
        self.galaxy_interactor = galaxy_interactor

    def load_workflow( self, name, content=workflow_str, add_pja=False ):
        workflow = json.loads( content )
        workflow[ "name" ] = name
        if add_pja:
            tool_step = workflow[ "steps" ][ "2" ]
            tool_step[ "post_job_actions" ][ "RenameDatasetActionout_file1" ] = dict(
                action_type="RenameDatasetAction",
                output_name="out_file1",
                action_arguments=dict( newname="foo ${replaceme}" ),
            )
        return workflow

    def load_random_x2_workflow( self, name ):
        return self.load_workflow( name, content=workflow_random_x2_str )

    def load_workflow_from_resource( self, name, filename=None ):
        if filename is None:
            filename = "%s.ga" % name
        content = resource_string( __name__, filename )
        return self.load_workflow( name, content=content )

    def simple_workflow( self, name, **create_kwds ):
        workflow = self.load_workflow( name )
        return self.create_workflow( workflow, **create_kwds )

    def create_workflow( self, workflow, **create_kwds ):
        data = dict(
            workflow=json.dumps( workflow ),
            **create_kwds
        )
        upload_response = self.galaxy_interactor.post( "workflows/upload", data=data )
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


class DatasetCollectionPopulator( object ):

    def __init__( self, galaxy_interactor ):
        self.galaxy_interactor = galaxy_interactor
        self.dataset_populator = DatasetPopulator( galaxy_interactor )

    def create_list_from_pairs( self, history_id, pairs ):
        element_identifiers = []
        for i, pair in enumerate( pairs ):
            element_identifiers.append( dict(
                name="test%d" % i,
                src="hdca",
                id=pair
            ) )

        payload = dict(
            instance_type="history",
            history_id=history_id,
            element_identifiers=json.dumps(element_identifiers),
            collection_type="list:paired",
        )
        return self.__create( payload )

    def create_pair_in_history( self, history_id, **kwds ):
        payload = self.create_pair_payload(
            history_id,
            instance_type="history",
            **kwds
        )
        return self.__create( payload )

    def create_list_in_history( self, history_id, **kwds ):
        payload = self.create_list_payload(
            history_id,
            instance_type="history",
            **kwds
        )
        return self.__create( payload )

    def create_list_payload( self, history_id, **kwds ):
        return self.__create_payload( history_id, identifiers_func=self.list_identifiers, collection_type="list", **kwds )

    def create_pair_payload( self, history_id, **kwds ):
        return self.__create_payload( history_id, identifiers_func=self.pair_identifiers, collection_type="paired", **kwds )

    def __create_payload( self, history_id, identifiers_func, collection_type, **kwds ):
        contents = None
        if "contents" in kwds:
            contents = kwds[ "contents" ]
            del kwds[ "contents" ]

        if "element_identifiers" not in kwds:
            kwds[ "element_identifiers" ] = json.dumps( identifiers_func( history_id, contents=contents ) )

        payload = dict(
            history_id=history_id,
            collection_type=collection_type,
            **kwds
        )
        return payload

    def pair_identifiers( self, history_id, contents=None ):
        hda1, hda2 = self.__datasets( history_id, count=2, contents=contents )

        element_identifiers = [
            dict( name="forward", src="hda", id=hda1[ "id" ] ),
            dict( name="reverse", src="hda", id=hda2[ "id" ] ),
        ]
        return element_identifiers

    def list_identifiers( self, history_id, contents=None ):
        count = 3 if not contents else len( contents )
        # Contents can be a list of strings (with name auto-assigned here) or a list of
        # 2-tuples of form (name, dataset_content).
        if contents and isinstance(contents[0], tuple):
            hdas = self.__datasets( history_id, count=count, contents=[c[1] for c in contents] )
            hda_to_identifier = lambda ( i, hda ): dict( name=contents[i][0], src="hda", id=hda[ "id" ] )
        else:
            hdas = self.__datasets( history_id, count=count, contents=contents )
            hda_to_identifier = lambda ( i, hda ): dict( name="data%d" % ( i + 1 ), src="hda", id=hda[ "id" ] )
        element_identifiers = map( hda_to_identifier, enumerate( hdas ) )
        return element_identifiers

    def __create( self, payload ):
        create_response = self.galaxy_interactor.post( "dataset_collections", data=payload )
        return create_response

    def __datasets( self, history_id, count, contents=None ):
        datasets = []
        for i in xrange( count ):
            new_kwds = {}
            if contents:
                new_kwds[ "content" ] = contents[ i ]
            datasets.append( self.dataset_populator.new_dataset( history_id, **new_kwds ) )
        return datasets


def wait_on_state( state_func, assert_ok=False, timeout=5 ):
    def get_state( ):
        response = state_func()
        assert response.status_code == 200, "Failed to fetch state update while waiting."
        state = response.json()[ "state" ]
        if state not in [ "running", "queued", "new" ]:
            if assert_ok:
                assert state == "ok", "Final state - %s - not okay." % state
            return state
        else:
            return None
    wait_on( get_state, desc="state", timeout=timeout)


def wait_on( function, desc, timeout=5 ):
    delta = .25
    iteration = 0
    while True:
        if (delta * iteration) > timeout:
            assert False, "Timed out waiting on %s." % desc
        iteration += 1
        value = function()
        if value is not None:
            return value
        time.sleep( delta )
