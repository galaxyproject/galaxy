import os
import sys
from base.twilltestcase import TwillTestCase
from base.interactor import GalaxyInteractorApi, stage_data_in_history

from galaxy.util import parse_xml
from galaxy.util import bunch
from galaxy.tools.test import parse_param_elem, require_file, test_data_iter, parse_output_elems
from json import load, dumps

from logging import getLogger
log = getLogger( __name__ )


class WorkflowTestCase( TwillTestCase ):
    """
    Kind of a shell of a test case for running workflow tests. Probably
    needs to look more like test_toolbox.
    """
    workflow_test_file = None
    user_api_key = None
    master_api_key = None

    def test_workflow( self, workflow_test_file=None ):
        maxseconds = 120
        workflow_test_file = workflow_test_file or WorkflowTestCase.workflow_test_file
        assert workflow_test_file
        workflow_test = parse_test_file( workflow_test_file )
        galaxy_interactor = GalaxyWorkflowInteractor( self )

        # Calling workflow https://github.com/jmchilton/blend4j/blob/master/src/test/java/com/github/jmchilton/blend4j/galaxy/WorkflowsTest.java

        # Import workflow
        workflow_id, step_id_map, output_defs = self.__import_workflow( galaxy_interactor, workflow_test.workflow )

        # Stage data and history for workflow
        test_history = galaxy_interactor.new_history()
        stage_data_in_history( galaxy_interactor, workflow_test.test_data(), test_history )

        # Build workflow parameters
        uploads = galaxy_interactor.uploads
        ds_map = {}
        for step_index, input_dataset_label in workflow_test.input_datasets():
            # Upload is {"src": "hda", "id": hid}
            try:
                upload = uploads[ workflow_test.upload_name( input_dataset_label ) ]
            except KeyError:
                raise AssertionError( "Failed to find upload with label %s in uploaded datasets %s" % ( input_dataset_label, uploads ) )

            ds_map[ step_id_map[ step_index ] ] = upload

        payload = {
            "history": "hist_id=%s" % test_history,
            "ds_map": dumps( ds_map ),
            "workflow_id": workflow_id,
        }
        run_response = galaxy_interactor.run_workflow( payload ).json()

        outputs = run_response[ 'outputs' ]
        if not len( outputs ) == len( output_defs ):
            msg_template = "Number of outputs [%d] created by workflow execution does not equal expected number from input file [%d]."
            msg = msg_template % ( len( outputs ), len( output_defs ) )
            raise AssertionError( msg )

        galaxy_interactor.wait_for_ids( test_history, outputs )

        for expected_output_def in workflow_test.outputs:
            # Get the correct hid
            name, outfile, attributes = expected_output_def
            output_testdef = bunch.Bunch( name=name, outfile=outfile, attributes=attributes )

            output_data = outputs[ int( name ) ]
            try:
                galaxy_interactor.verify_output( test_history, output_data, output_testdef=output_testdef, shed_tool_id=None, maxseconds=maxseconds )
            except Exception:
                for stream in ['stdout', 'stderr']:
                    stream_output = galaxy_interactor.get_job_stream( test_history, output_data, stream=stream )
                    print >>sys.stderr, self._format_stream( stream_output, stream=stream, format=True )
                raise

    def __import_workflow( self, galaxy_interactor, workflow ):
        """
        Import workflow into Galaxy and return id and mapping of step ids.
        """
        workflow_info = galaxy_interactor.import_workflow( workflow ).json()
        try:
            workflow_id = workflow_info[ 'id' ]
        except KeyError:
            raise AssertionError( "Failed to find id for workflow import response %s" % workflow_info )

        # Well ideally the local copy of the workflow would have the same step ids
        # as the one imported through the API, but API workflow imports are 1-indexed
        # and GUI exports 0-indexed as of mid-november 2013.

        imported_workflow = galaxy_interactor.read_workflow( workflow_id )
        #log.info("local %s\nimported%s" % (workflow, imported_workflow))
        step_id_map = {}
        local_steps_ids = sorted( [ int( step_id ) for step_id in workflow[ 'steps' ].keys() ] )
        imported_steps_ids = sorted( [ int( step_id ) for step_id in imported_workflow[ 'steps' ].keys() ] )
        for local_step_id, imported_step_id in zip( local_steps_ids, imported_steps_ids ):
            step_id_map[ local_step_id ] = imported_step_id

        output_defs = []
        for local_step_id in local_steps_ids:
            step_def = workflow['steps'][ str( local_step_id ) ]
            output_defs.extend( step_def.get( "outputs", [] ) )

        return workflow_id, step_id_map, output_defs


def parse_test_file( workflow_test_file ):
    tree = parse_xml( workflow_test_file )
    root = tree.getroot()
    input_elems = root.findall( "input" )
    required_files = []
    dataset_dict = {}
    for input_elem in input_elems:
        name, value, attrib = parse_param_elem( input_elem )
        require_file( name, value, attrib, required_files )
        dataset_dict[ name ] = value

    outputs = parse_output_elems( root )

    workflow_file_rel_path = root.get( 'file' )
    if not workflow_file_rel_path:
        raise Exception( "Workflow test XML must declare file attribute pointing to workflow under test." )

    # TODO: Normalize this path, prevent it from accessing arbitrary files on system.
    worfklow_file_abs_path = os.path.join( os.path.dirname( workflow_test_file ), workflow_file_rel_path )

    return WorkflowTest(
        dataset_dict,
        required_files,
        worfklow_file_abs_path,
        outputs=outputs,
    )


class WorkflowTest( object ):

    def __init__( self, dataset_dict, required_files, workflow_file, outputs ):
        self.dataset_dict = dataset_dict
        self.required_files = required_files
        self.workflow = load( open( workflow_file, "r" ) )
        self.outputs = outputs

    def test_data( self ):
        return test_data_iter( self.required_files )

    def upload_name( self, input_dataset_label ):
        return self.dataset_dict[ input_dataset_label ]

    def input_datasets( self ):
        steps = self.workflow[ "steps" ]
        log.info("in input_datasets with steps %s" % steps)
        for step_index, step_dict in steps.iteritems():
            if step_dict.get( "name", None ) == "Input dataset":
                yield int( step_index ), step_dict[ "inputs" ][0][ "name" ]


class GalaxyWorkflowInteractor(GalaxyInteractorApi):

    def __init__( self, twill_test_case ):
        super(GalaxyWorkflowInteractor, self).__init__( twill_test_case )

    def import_workflow( self, workflow_rep ):
        payload = { "workflow": dumps( workflow_rep ) }
        return self._post( "workflows/upload", data=payload )

    def run_workflow( self, data ):
        return self._post( "workflows", data=data )

    def read_workflow( self, id ):
        return self._get( "workflows/%s" % id ).json()

    def wait_for_ids( self, history_id, ids ):
        self.twill_test_case.wait_for( lambda: not all( [ self.__dataset_ready( history_id, id ) for id in ids ] ), maxseconds=120 )

    def __dataset_ready( self, history_id, id ):
        contents = self._get( 'histories/%s/contents' % history_id ).json()
        for content in contents:

            if content["id"] == id:
                state = content[ 'state' ]
                state_ready = self._state_ready( state, error_msg="Dataset creation failed for dataset with name %s." % content[ 'name' ] )
                return state_ready
        return False
