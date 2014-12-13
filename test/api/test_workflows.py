from .helpers import wait_on_state

from base import api
from json import dumps
from collections import namedtuple

import time

import yaml
from .helpers import WorkflowPopulator
from .helpers import DatasetPopulator
from .helpers import DatasetCollectionPopulator
from .helpers import skip_without_tool

from .yaml_to_workflow import yaml_to_workflow

from requests import delete
from requests import put

from galaxy.exceptions import error_codes


class BaseWorkflowsApiTestCase( api.ApiTestCase ):
    # TODO: Find a new file for this class.

    def setUp( self ):
        super( BaseWorkflowsApiTestCase, self ).setUp()
        self.workflow_populator = WorkflowPopulator( self.galaxy_interactor )
        self.dataset_populator = DatasetPopulator( self.galaxy_interactor )
        self.dataset_collection_populator = DatasetCollectionPopulator( self.galaxy_interactor )

    def _assert_user_has_workflow_with_name( self, name ):
        names = self._workflow_names()
        assert name in names, "No workflows with name %s in users workflows <%s>" % ( name, names )

    def _workflow_names( self ):
        index_response = self._get( "workflows" )
        self._assert_status_code_is( index_response, 200 )
        names = map( lambda w: w[ "name" ], index_response.json() )
        return names

    def _upload_yaml_workflow(self, has_yaml):
        workflow = yaml_to_workflow(has_yaml)
        workflow_str = dumps(workflow, indent=4)
        data = {
            'workflow': workflow_str
        }
        upload_response = self._post( "workflows", data=data )
        self._assert_status_code_is( upload_response, 200 )
        self._assert_user_has_workflow_with_name( "%s (imported from API)" % ( workflow[ "name" ] ) )
        return upload_response.json()[ "id" ]

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

    def _ds_entry( self, hda ):
        src = 'hda'
        if 'history_content_type' in hda and hda[ 'history_content_type' ] == "dataset_collection":
            src = 'hdca'
        return dict( src=src, id=hda[ "id" ] )

    def _workflow_inputs( self, uploaded_workflow_id ):
        workflow_show_resposne = self._get( "workflows/%s" % uploaded_workflow_id )
        self._assert_status_code_is( workflow_show_resposne, 200 )
        workflow_inputs = workflow_show_resposne.json()[ "inputs" ]
        return workflow_inputs

    def _invocation_details( self, workflow_id, invocation_id ):
        invocation_details_response = self._get( "workflows/%s/usage/%s" % ( workflow_id, invocation_id ) )
        self._assert_status_code_is( invocation_details_response, 200 )
        invocation_details = invocation_details_response.json()
        return invocation_details

    def _run_jobs( self, jobs_yaml, history_id=None ):
        if history_id is None:
            history_id = self.history_id
        workflow_id = self._upload_yaml_workflow(
            jobs_yaml
        )
        jobs_descriptions = yaml.load( jobs_yaml )
        test_data = jobs_descriptions["test_data"]

        label_map = {}
        inputs = {}
        for key, value in test_data.items():
            if isinstance( value, dict ):
                elements_data = value.get( "elements", [] )
                elements = []
                for element_data in elements_data:
                    identifier = element_data[ "identifier" ]
                    content = element_data["content"]
                    elements.append( ( identifier, content ) )
                collection_type = value["type"]
                if collection_type == "list:paired":
                    hdca = self.dataset_collection_populator.create_list_of_pairs_in_history( history_id ).json()
                elif collection_type == "list":
                    hdca = self.dataset_collection_populator.create_list_in_history( history_id, contents=elements ).json()
                else:
                    hdca = self.dataset_collection_populator.create_pair_in_history( history_id, contents=elements ).json()
                label_map[key] = self._ds_entry( hdca )
                inputs[key] = hdca
            else:
                hda = self.dataset_populator.new_dataset( history_id, content=value )
                label_map[key] = self._ds_entry( hda )
                inputs[key] = hda
        workflow_request = dict(
            history="hist_id=%s" % history_id,
            workflow_id=workflow_id,
        )
        workflow_request[ "inputs" ] = dumps( label_map )
        workflow_request[ "inputs_by" ] = 'name'
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        url = "workflows/%s/usage" % ( workflow_id )
        invocation_response = self._post( url, data=workflow_request )
        self._assert_status_code_is( invocation_response, 200 )
        invocation = invocation_response.json()
        invocation_id = invocation[ "id" ]
        # Wait for workflow to become fully scheduled and then for all jobs
        # complete.
        self.wait_for_invocation( workflow_id, invocation_id )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        jobs = self._history_jobs( history_id )
        return RunJobsSummary(
            history_id=history_id,
            workflow_id=workflow_id,
            inputs=inputs,
            jobs=jobs,
        )

    def wait_for_invocation( self, workflow_id, invocation_id ):
        url = "workflows/%s/usage/%s" % ( workflow_id, invocation_id )
        return wait_on_state( lambda: self._get( url )  )

    def _history_jobs( self, history_id ):
        return self._get("jobs", { "history_id": history_id, "order_by": "create_time" } ).json()


# Workflow API TODO:
# - Allow history_id as param to workflow run action. (hist_id)
# - Allow post to workflows/<workflow_id>/run in addition to posting to
#    /workflows with id in payload.
# - Much more testing obviously, always more testing.
class WorkflowsApiTestCase( BaseWorkflowsApiTestCase ):

    def setUp( self ):
        super( WorkflowsApiTestCase, self ).setUp()

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
        assert workflow_name not in self._workflow_names()

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

    def test_import_annotations( self ):
        workflow_id = self.workflow_populator.simple_workflow( "test_import_annotations", publish=True )
        with self._different_user():
            other_import_response = self.__import_workflow( workflow_id )
            self._assert_status_code_is( other_import_response, 200 )

            # Test annotations preserved during upload and copied over during
            # import.
            other_id = other_import_response.json()["id"]
            download_response = self._get( "workflows/%s" % other_id )
            imported_workflow = download_response.json()
            assert imported_workflow["annotation"] == "simple workflow", download_response.json()
            step_annotations = set(map(lambda step: step["annotation"], imported_workflow["steps"].values()))
            assert "input1 description" in step_annotations

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

        invocation_id = run_workflow_response.json()[ "id" ]
        invocation = self._invocation_details( workflow_request[ "workflow_id" ], invocation_id )
        assert invocation[ "state" ] == "scheduled", invocation

        self._assert_status_code_is( run_workflow_response, 200 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )

    def test_workflow_request( self ):
        workflow = self.workflow_populator.load_workflow( name="test_for_queue" )
        workflow_request, history_id = self._setup_workflow_run( workflow )
        url = "workflows/%s/usage" % ( workflow_request[ "workflow_id" ] )
        del workflow_request[ "workflow_id" ]
        run_workflow_response = self._post( url, data=workflow_request )

        self._assert_status_code_is( run_workflow_response, 200 )
        # Give some time for workflow to get scheduled before scanning the history.
        time.sleep( 5 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )

    def test_workflow_pause( self ):
        workflow = self.workflow_populator.load_workflow_from_resource( "test_workflow_pause" )
        uploaded_workflow_id = self.workflow_populator.create_workflow( workflow )
        history_id = self.dataset_populator.new_history()
        hda1 = self.dataset_populator.new_dataset( history_id, content="1 2 3" )
        index_map = {
            '0': self._ds_entry(hda1),
        }
        invocation_id = self.__invoke_workflow( history_id, uploaded_workflow_id, index_map )
        # Give some time for workflow to get scheduled before scanning the history.
        time.sleep( 5 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )

        # Wait for all the datasets to complete, make sure the workflow invocation
        # is not complete.
        invocation = self._invocation_details( uploaded_workflow_id, invocation_id )
        assert invocation[ 'state' ] != 'scheduled', invocation

        self.__review_paused_steps( uploaded_workflow_id, invocation_id, order_index=2, action=True )

        time.sleep( 5 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        invocation = self._invocation_details( uploaded_workflow_id, invocation_id )
        assert invocation[ 'state' ] == 'scheduled', invocation

    def test_workflow_pause_cancel( self ):
        workflow = self.workflow_populator.load_workflow_from_resource( "test_workflow_pause" )
        uploaded_workflow_id = self.workflow_populator.create_workflow( workflow )
        history_id = self.dataset_populator.new_history()
        hda1 = self.dataset_populator.new_dataset( history_id, content="1 2 3" )
        index_map = {
            '0': self._ds_entry(hda1),
        }
        invocation_id = self.__invoke_workflow( history_id, uploaded_workflow_id, index_map )
        # Give some time for workflow to get scheduled before scanning the history.
        time.sleep( 5 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )

        # Wait for all the datasets to complete, make sure the workflow invocation
        # is not complete.
        invocation = self._invocation_details( uploaded_workflow_id, invocation_id )
        assert invocation[ 'state' ] != 'scheduled'

        self.__review_paused_steps( uploaded_workflow_id, invocation_id, order_index=2, action=False )
        # Not immediately cancelled, must wait until workflow scheduled again.
        time.sleep( 4 )
        invocation = self._invocation_details( uploaded_workflow_id, invocation_id )
        assert invocation[ 'state' ] == 'cancelled', invocation

    def test_workflow_map_reduce_pause( self ):
        workflow = self.workflow_populator.load_workflow_from_resource( "test_workflow_map_reduce_pause" )
        uploaded_workflow_id = self.workflow_populator.create_workflow( workflow )
        history_id = self.dataset_populator.new_history()
        hda1 = self.dataset_populator.new_dataset( history_id, content="reviewed\nunreviewed" )
        hdca1 = self.dataset_collection_populator.create_list_in_history( history_id, contents=["1\n2\n3", "4\n5\n6"] ).json()
        index_map = {
            '0': self._ds_entry(hda1),
            '1': self._ds_entry(hdca1),
        }
        invocation_id = self.__invoke_workflow( history_id, uploaded_workflow_id, index_map )
        # Give some time for workflow to get scheduled before scanning the history.
        time.sleep( 5 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )

        # Wait for all the datasets to complete, make sure the workflow invocation
        # is not complete.
        invocation = self._invocation_details( uploaded_workflow_id, invocation_id )
        assert invocation[ 'state' ] != 'scheduled'

        self.__review_paused_steps( uploaded_workflow_id, invocation_id, order_index=4, action=True )

        time.sleep( 5 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        invocation = self._invocation_details( uploaded_workflow_id, invocation_id )
        assert invocation[ 'state' ] == 'scheduled'
        self.assertEquals("reviewed\n1\nreviewed\n4\n", self.dataset_populator.get_history_dataset_content( history_id ) )

    def test_cancel_workflow_invocation( self ):
        workflow = self.workflow_populator.load_workflow_from_resource( "test_workflow_pause" )
        uploaded_workflow_id = self.workflow_populator.create_workflow( workflow )
        history_id = self.dataset_populator.new_history()
        hda1 = self.dataset_populator.new_dataset( history_id, content="1 2 3" )
        index_map = {
            '0': self._ds_entry(hda1),
        }
        invocation_id = self.__invoke_workflow( history_id, uploaded_workflow_id, index_map )
        # Give some time for workflow to get scheduled before scanning the history.
        time.sleep( 5 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )

        # Wait for all the datasets to complete, make sure the workflow invocation
        # is not complete.
        invocation = self._invocation_details( uploaded_workflow_id, invocation_id )
        assert invocation[ 'state' ] != 'scheduled'

        invocation_url = self._api_url( "workflows/%s/usage/%s" % (uploaded_workflow_id, invocation_id), use_key=True )
        delete_response = delete( invocation_url )
        self._assert_status_code_is( delete_response, 200 )

        # Wait for all the datasets to complete, make sure the workflow invocation
        # is not complete.
        invocation = self._invocation_details( uploaded_workflow_id, invocation_id )
        assert invocation[ 'state' ] == 'cancelled'

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
        workflow_request, history_id, steps = self._setup_random_x2_workflow_steps( "test_for_replace_step_params" )
        params = dumps( { str(steps[1]["id"]): dict( num_lines=5 ) } )
        workflow_request[ "parameters" ] = params
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        # Would be 8 and 6 without modification
        self.__assert_lines_hid_line_count_is( history_id, 2, 8 )
        self.__assert_lines_hid_line_count_is( history_id, 3, 5 )

    @skip_without_tool( "random_lines1" )
    def test_run_replace_params_nested( self ):
        workflow_request, history_id, steps = self._setup_random_x2_workflow_steps( "test_for_replace_step_params_nested" )
        seed_source = dict(
            seed_source_selector="set_seed",
            seed="moo",
        )
        params = dumps( { str(steps[0]["id"]): dict( num_lines=1, seed_source=seed_source ),
                          str(steps[1]["id"]): dict( num_lines=1, seed_source=seed_source ) } )
        workflow_request[ "parameters" ] = params
        run_workflow_response = self._post( "workflows", data=workflow_request )
        self._assert_status_code_is( run_workflow_response, 200 )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        self.assertEquals("3\n", self.dataset_populator.get_history_dataset_content( history_id ) )

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
        invocation_id = usage[ "id" ]
        usage_details = self._invocation_details( workflow_id, invocation_id )
        # Assert some high-level things about the structure of data returned.
        self._assert_has_keys( usage_details, "inputs", "steps" )
        invocation_steps = usage_details[ "steps" ]
        for step in invocation_steps:
            self._assert_has_keys( step, "workflow_step_id", "order_index", "id" )
        an_invocation_step = invocation_steps[ 0 ]
        step_id = an_invocation_step[ "id" ]
        step_response = self._get( "workflows/%s/usage/%s/steps/%s" % ( workflow_id, invocation_id, step_id ) )
        self._assert_status_code_is( step_response, 200 )
        self._assert_has_keys( step_response.json(), "id", "order_index" )

    def _invocation_step_details( self, workflow_id, invocation_id, step_id ):
        invocation_step_response = self._get( "workflows/%s/usage/%s/steps/%s" % ( workflow_id, invocation_id, step_id ) )
        self._assert_status_code_is( invocation_step_response, 200 )
        invocation_step_details = invocation_step_response.json()
        return invocation_step_details

    def _execute_invocation_step_action( self, workflow_id, invocation_id, step_id, action ):
        raw_url = "workflows/%s/usage/%s/steps/%s" % ( workflow_id, invocation_id, step_id )
        url = self._api_url( raw_url, use_key=True )
        payload = dumps( dict( action=action ) )
        action_response = put( url, data=payload )
        self._assert_status_code_is( action_response, 200 )
        invocation_step_details = action_response.json()
        return invocation_step_details

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

    def _setup_random_x2_workflow_steps( self, name ):
        workflow_request, history_id = self._setup_random_x2_workflow( "test_for_replace_step_params" )
        random_line_steps = self._random_lines_steps( workflow_request )
        return workflow_request, history_id, random_line_steps

    def _random_lines_steps( self, workflow_request ):
        workflow_summary_response = self._get( "workflows/%s" % workflow_request[ "workflow_id" ] )
        self._assert_status_code_is( workflow_summary_response, 200 )
        steps = workflow_summary_response.json()[ "steps" ]
        return sorted( filter(lambda step: step["tool_id"] == "random_lines1", steps.values()), key=lambda step: step["id"] )

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

    def __review_paused_steps( self, uploaded_workflow_id, invocation_id, order_index, action=True ):
        invocation = self._invocation_details( uploaded_workflow_id, invocation_id )
        invocation_steps = invocation[ "steps" ]
        pause_steps = [ s for s in invocation_steps if s[ 'order_index' ] == order_index ]
        for pause_step in pause_steps:
            pause_step_id = pause_step[ 'id' ]

            self._execute_invocation_step_action( uploaded_workflow_id, invocation_id, pause_step_id, action=action )

    def __assert_lines_hid_line_count_is( self, history, hid, lines ):
        contents_url = "histories/%s/contents" % history
        history_contents_response = self._get( contents_url )
        self._assert_status_code_is( history_contents_response, 200 )
        hda_summary = filter( lambda hc: hc[ "hid" ] == hid, history_contents_response.json() )[ 0 ]
        hda_info_response = self._get( "%s/%s" % ( contents_url, hda_summary[ "id" ] ) )
        self._assert_status_code_is( hda_info_response, 200 )
        self.assertEquals( hda_info_response.json()[ "metadata_data_lines" ], lines )

    def __invoke_workflow( self, history_id, workflow_id, inputs, assert_ok=True ):
        workflow_request = dict(
            history="hist_id=%s" % history_id,
        )
        workflow_request[ "inputs" ] = dumps( inputs )
        workflow_request[ "inputs_by" ] = 'step_index'
        url = "workflows/%s/usage" % ( workflow_id )

        invocation_response = self._post( url, data=workflow_request )
        if assert_ok:
            self._assert_status_code_is( invocation_response, 200 )
            invocation_id = invocation_response.json()[ "id" ]
            return invocation_id
        else:
            return invocation_response

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


RunJobsSummary = namedtuple('RunJobsSummary', ['history_id', 'workflow_id', 'inputs', 'jobs'])

