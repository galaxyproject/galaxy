import json
import time

from operator import itemgetter

import requests

from pkg_resources import resource_string
from six import StringIO

from base import api_asserts

# Simple workflow that takes an input and call cat wrapper on it.
workflow_str = resource_string( __name__, "data/test_workflow_1.ga" )
# Simple workflow that takes an input and filters with random lines twice in a
# row - first grabbing 8 lines at random and then 6.
workflow_random_x2_str = resource_string( __name__, "data/test_workflow_2.ga" )


DEFAULT_TIMEOUT = 15  # Secs to wait for state to turn ok


def skip_without_tool( tool_id ):
    """ Decorate an API test method as requiring a specific tool,
    have nose skip the test case is the tool is unavailable.
    """

    def method_wrapper( method ):

        def get_tool_ids( api_test_case ):
            index = api_test_case.galaxy_interactor.get( "tools", data=dict(in_panel=False) )
            tools = index.json()
            # In panels by default, so flatten out sections...
            tool_ids = [itemgetter( "id" )(_) for _ in tools]
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


class BaseDatasetPopulator( object ):
    """ Abstract description of API operations optimized for testing
    Galaxy - implementations must implement _get and _post.
    """

    def new_dataset( self, history_id, content='TestData123', wait=False, **kwds ):
        payload = self.upload_payload( history_id, content, **kwds )
        run_response = self._post( "tools", data=payload ).json()
        if wait:
            job = run_response["jobs"][0]
            self.wait_for_job(job["id"])
            self.wait_for_history(history_id, assert_ok=True)
        return run_response["outputs"][0]

    def wait_for_history( self, history_id, assert_ok=False, timeout=DEFAULT_TIMEOUT ):
        try:
            return wait_on_state( lambda: self._get( "histories/%s" % history_id ), assert_ok=assert_ok, timeout=timeout )
        except AssertionError:
            self._summarize_history_errors( history_id )
            raise

    def wait_for_job( self, job_id, assert_ok=False, timeout=DEFAULT_TIMEOUT ):
        return wait_on_state( lambda: self.get_job_details( job_id ), assert_ok=assert_ok, timeout=timeout )

    def get_job_details( self, job_id, full=False ):
        return self._get( "jobs/%s?full=%s" % (job_id, full) )

    def _summarize_history_errors( self, history_id ):
        pass

    def new_history( self, **kwds ):
        name = kwds.get( "name", "API Test History" )
        create_history_response = self._post( "histories", data=dict( name=name ) )
        history_id = create_history_response.json()[ "id" ]
        return history_id

    def upload_payload( self, history_id, content, **kwds ):
        name = kwds.get( "name", "Test Dataset" )
        dbkey = kwds.get( "dbkey", "?" )
        file_type = kwds.get( "file_type", 'txt' )
        upload_params = {
            'files_0|NAME': name,
            'dbkey': dbkey,
            'file_type': file_type,
        }
        if hasattr(content, 'read'):
            upload_params[ "files_0|file_data"] = content
        else:
            upload_params[ 'files_0|url_paste' ] = content

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
        if "files_0|file_data" in inputs:
            kwds[ "__files" ] = { "files_0|file_data": inputs[ "files_0|file_data" ] }
            del inputs[ "files_0|file_data" ]

        return dict(
            tool_id=tool_id,
            inputs=json.dumps(inputs),
            history_id=history_id,
            **kwds
        )

    def run_tool( self, tool_id, inputs, history_id, **kwds ):
        payload = self.run_tool_payload( tool_id, inputs, history_id, **kwds )
        tool_response = self._post( "tools", data=payload )
        api_asserts.assert_status_code_is( tool_response, 200 )
        return tool_response.json()

    def get_history_dataset_content( self, history_id, wait=True, **kwds ):
        dataset_id = self.__history_content_id( history_id, wait=wait, **kwds )
        display_response = self.__get_contents_request( history_id, "/%s/display" % dataset_id )
        assert display_response.status_code == 200, display_response.content
        return display_response.content

    def get_history_dataset_details( self, history_id, **kwds ):
        dataset_id = self.__history_content_id( history_id, **kwds )
        details_response = self.__get_contents_request( history_id, "/datasets/%s" % dataset_id )
        assert details_response.status_code == 200
        return details_response.json()

    def get_history_collection_details( self, history_id, **kwds ):
        hdca_id = self.__history_content_id( history_id, **kwds )
        details_response = self.__get_contents_request( history_id, "/dataset_collections/%s" % hdca_id )
        assert details_response.status_code == 200, details_response.content
        return details_response.json()

    def __history_content_id( self, history_id, wait=True, **kwds ):
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
        return self._get( url )


class DatasetPopulator( BaseDatasetPopulator ):

    def __init__( self, galaxy_interactor ):
        self.galaxy_interactor = galaxy_interactor

    def _post( self, route, data={}, files=None ):
        files = data.get( "__files", None )
        if files is not None:
            del data[ "__files" ]

        return self.galaxy_interactor.post( route, data, files=files )

    def _get( self, route ):
        return self.galaxy_interactor.get( route )

    def _summarize_history_errors( self, history_id ):
        self.galaxy_interactor._summarize_history_errors( history_id )


class BaseWorkflowPopulator( object ):

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
            filename = "data/%s.ga" % name
        content = resource_string( __name__, filename )
        return self.load_workflow( name, content=content )

    def simple_workflow( self, name, **create_kwds ):
        workflow = self.load_workflow( name )
        return self.create_workflow( workflow, **create_kwds )

    def create_workflow( self, workflow, **create_kwds ):
        upload_response = self.create_workflow_response( workflow, **create_kwds )
        uploaded_workflow_id = upload_response.json()[ "id" ]
        return uploaded_workflow_id

    def create_workflow_response( self, workflow, **create_kwds ):
        data = dict(
            workflow=json.dumps( workflow ),
            **create_kwds
        )
        upload_response = self._post( "workflows/upload", data=data )
        return upload_response

    def wait_for_invocation( self, workflow_id, invocation_id, timeout=DEFAULT_TIMEOUT ):
        url = "workflows/%s/usage/%s" % ( workflow_id, invocation_id )
        return wait_on_state( lambda: self._get( url ), timeout=timeout  )

    def wait_for_workflow( self, workflow_id, invocation_id, history_id, assert_ok=True, timeout=DEFAULT_TIMEOUT ):
        """ Wait for a workflow invocation to completely schedule and then history
        to be complete. """
        self.wait_for_invocation( workflow_id, invocation_id, timeout=timeout )
        self.dataset_populator.wait_for_history( history_id, assert_ok=assert_ok, timeout=timeout )


class WorkflowPopulator( BaseWorkflowPopulator ):

    def __init__( self, galaxy_interactor ):
        self.galaxy_interactor = galaxy_interactor
        self.dataset_populator = DatasetPopulator( galaxy_interactor )

    def _post( self, route, data={} ):
        return self.galaxy_interactor.post( route, data )

    def _get( self, route ):
        return self.galaxy_interactor.get( route )


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
            "files_0|file_data": kwds.get( "file", StringIO( kwds.get( "contents", "TestData" ) ) ),
        }
        return create_data, files

    def new_library_dataset( self, name, **create_dataset_kwds ):
        library = self.new_private_library( name )
        payload, files = self.create_dataset_request( library, **create_dataset_kwds )
        url_rel = "libraries/%s/contents" % ( library[ "id" ] )
        dataset = self.api_test_case.galaxy_interactor.post( url_rel, payload, files=files ).json()[0]

        def show():
            return self.api_test_case.galaxy_interactor.get( "libraries/%s/contents/%s" % ( library[ "id" ], dataset[ "id" ] ) )

        wait_on_state(show, timeout=DEFAULT_TIMEOUT)
        return show().json()


class BaseDatasetCollectionPopulator( object ):

    def create_list_from_pairs( self, history_id, pairs, name="Dataset Collection from pairs" ):
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
            name=name,
        )
        return self.__create( payload )

    def create_list_of_pairs_in_history( self, history_id, **kwds ):
        pair1 = self.create_pair_in_history( history_id, **kwds ).json()["id"]
        return self.create_list_from_pairs( history_id, [ pair1 ] )

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

        if "name" not in kwds:
            kwds["name"] = "Test Dataset Collection"

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

            def hda_to_identifier(i, hda):
                return dict(name=contents[i][0], src="hda", id=hda["id"])
        else:
            hdas = self.__datasets( history_id, count=count, contents=contents )

            def hda_to_identifier(i, hda):
                return dict(name="data%d" % (i + 1), src="hda", id=hda["id"])
        element_identifiers = [hda_to_identifier(i, hda) for (i, hda) in enumerate(hdas)]
        return element_identifiers

    def __create( self, payload ):
        return self._create_collection( payload )

    def __datasets( self, history_id, count, contents=None ):
        datasets = []
        for i in range( count ):
            new_kwds = {}
            if contents:
                new_kwds[ "content" ] = contents[ i ]
            datasets.append( self.dataset_populator.new_dataset( history_id, **new_kwds ) )
        return datasets


class DatasetCollectionPopulator( BaseDatasetCollectionPopulator ):

    def __init__( self, galaxy_interactor ):
        self.galaxy_interactor = galaxy_interactor
        self.dataset_populator = DatasetPopulator( galaxy_interactor )

    def _create_collection( self, payload ):
        create_response = self.galaxy_interactor.post( "dataset_collections", data=payload )
        return create_response


def wait_on_state( state_func, assert_ok=False, timeout=DEFAULT_TIMEOUT ):
    def get_state( ):
        response = state_func()
        assert response.status_code == 200, "Failed to fetch state update while waiting."
        state = response.json()[ "state" ]
        if state not in [ "running", "queued", "new", "ready" ]:
            if assert_ok:
                assert state == "ok", "Final state - %s - not okay." % state
            return state
        else:
            return None
    return wait_on( get_state, desc="state", timeout=timeout)


class GiPostGetMixin:
    """Mixin for adapting Galaxy testing populators helpers to bioblend."""

    def _get(self, route):
        return self._gi.make_get_request(self.__url(route))

    def _post(self, route, data={}):
        data = data.copy()
        data['key'] = self._gi.key
        return requests.post(self.__url(route), data=data)

    def __url(self, route):
        return self._gi.url + "/" + route


class GiDatasetPopulator(BaseDatasetPopulator, GiPostGetMixin):

    """Implementation of BaseDatasetPopulator backed by bioblend."""

    def __init__(self, gi):
        """Construct a dataset populator from a bioblend GalaxyInstance."""
        self._gi = gi


class GiDatasetCollectionPopulator(BaseDatasetCollectionPopulator, GiPostGetMixin):

    """Implementation of BaseDatasetCollectionPopulator backed by bioblend."""

    def __init__(self, gi):
        """Construct a dataset collection populator from a bioblend GalaxyInstance."""
        self._gi = gi
        self.dataset_populator = GiDatasetPopulator(gi)

    def _create_collection(self, payload):
        create_response = self._post( "dataset_collections", data=payload )
        return create_response


class GiWorkflowPopulator(BaseWorkflowPopulator, GiPostGetMixin):

    """Implementation of BaseWorkflowPopulator backed by bioblend."""

    def __init__(self, gi):
        """Construct a workflow populator from a bioblend GalaxyInstance."""
        self._gi = gi
        self.dataset_populator = GiDatasetPopulator(gi)


def wait_on( function, desc, timeout=DEFAULT_TIMEOUT ):
    delta = .25
    iteration = 0
    while True:
        total_wait = delta * iteration
        if total_wait > timeout:
            timeout_message = "Timed out after %s seconds waiting on %s." % (
                total_wait, desc
            )
            assert False, timeout_message
        iteration += 1
        value = function()
        if value is not None:
            return value
        time.sleep( delta )
