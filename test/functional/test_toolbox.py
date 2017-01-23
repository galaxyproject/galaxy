from __future__ import print_function

import logging
import new
import sys

try:
    from nose.tools import nottest
except ImportError:
    def nottest(x):
        return x

from base.instrument import register_job_data
from base.interactor import build_interactor, RunToolException, stage_data_in_history
from base.twilltestcase import TwillTestCase
from galaxy.tools import DataManagerTool
from galaxy.tools.verify.asserts import verify_assertions
from galaxy.util import bunch

log = logging.getLogger( __name__ )

toolbox = None

# Do not test Data Managers as part of the standard Tool Test Framework.
TOOL_TYPES_NO_TEST = ( DataManagerTool, )


class ToolTestCase( TwillTestCase ):
    """Abstract test case that runs tests based on a `galaxy.tools.test.ToolTest`"""

    def do_it( self, testdef, resource_parameters={} ):
        """
        Run through a tool test case.
        """
        shed_tool_id = self.shed_tool_id

        self._handle_test_def_errors( testdef )

        galaxy_interactor = self._galaxy_interactor( testdef )

        test_history = galaxy_interactor.new_history()

        stage_data_in_history( galaxy_interactor, testdef.test_data(), test_history, shed_tool_id )

        # Once data is ready, run the tool and check the outputs - record API
        # input, job info, tool run exception, as well as exceptions related to
        # job output checking and register they with the test plugin so it can
        # record structured information.
        tool_inputs = None
        job_stdio = None
        job_output_exceptions = None
        tool_execution_exception = None
        expected_failure_occurred = False
        try:
            try:
                tool_response = galaxy_interactor.run_tool( testdef, test_history, resource_parameters=resource_parameters )
                data_list, jobs, tool_inputs = tool_response.outputs, tool_response.jobs, tool_response.inputs
                data_collection_list = tool_response.output_collections
            except RunToolException as e:
                tool_inputs = e.inputs
                tool_execution_exception = e
                if not testdef.expect_failure:
                    raise e
                else:
                    expected_failure_occurred = True
            except Exception as e:
                tool_execution_exception = e
                raise e

            if not expected_failure_occurred:
                self.assertTrue( data_list or data_collection_list )

                try:
                    job_stdio = self._verify_outputs( testdef, test_history, jobs, shed_tool_id, data_list, data_collection_list, galaxy_interactor )
                except JobOutputsError as e:
                    job_stdio = e.job_stdio
                    job_output_exceptions = e.output_exceptions
                    raise e
                except Exception as e:
                    job_output_exceptions = [e]
                    raise e
        finally:
            job_data = {}
            if tool_inputs is not None:
                job_data["inputs"] = tool_inputs
            if job_stdio is not None:
                job_data["job"] = job_stdio
            if job_output_exceptions:
                job_data["output_problems"] = [str(_) for _ in job_output_exceptions]
            if tool_execution_exception:
                job_data["execution_problem"] = str(tool_execution_exception)
            register_job_data(job_data)

        galaxy_interactor.delete_history( test_history )

    def _galaxy_interactor( self, testdef ):
        return build_interactor( self, testdef.interactor )

    def _handle_test_def_errors(self, testdef):
        # If the test generation had an error, raise
        if testdef.error:
            if testdef.exception:
                raise testdef.exception
            else:
                raise Exception( "Test parse failure" )

    def _verify_outputs( self, testdef, history, jobs, shed_tool_id, data_list, data_collection_list, galaxy_interactor ):
        assert len(jobs) == 1, "Test framework logic error, somehow tool test resulted in more than one job."
        job = jobs[ 0 ]

        maxseconds = testdef.maxseconds
        if testdef.num_outputs is not None:
            expected = testdef.num_outputs
            actual = len( data_list )
            if expected != actual:
                messaage_template = "Incorrect number of outputs - expected %d, found %s."
                message = messaage_template % ( expected, actual )
                raise Exception( message )
        found_exceptions = []

        def register_exception(e):
            if not found_exceptions:
                # Only print this stuff out once.
                for stream in ['stdout', 'stderr']:
                    if stream in job_stdio:
                        print(self._format_stream( job_stdio[ stream ], stream=stream, format=True ), file=sys.stderr)
            found_exceptions.append(e)

        if testdef.expect_failure:
            if testdef.outputs:
                raise Exception("Cannot specify outputs in a test expecting failure.")

        # Wait for the job to complete and register expections if the final
        # status was not what test was expecting.
        job_failed = False
        try:
            galaxy_interactor.wait_for_job( job[ 'id' ], history, maxseconds )
        except Exception as e:
            job_failed = True
            if not testdef.expect_failure:
                found_exceptions.append(e)

        job_stdio = galaxy_interactor.get_job_stdio( job[ 'id' ] )

        if not job_failed and testdef.expect_failure:
            error = AssertionError("Expected job to fail but Galaxy indicated the job successfully completed.")
            register_exception(error)

        expect_exit_code = testdef.expect_exit_code
        if expect_exit_code is not None:
            exit_code = job_stdio["exit_code"]
            if str(expect_exit_code) != str(exit_code):
                error = AssertionError("Expected job to complete with exit code %s, found %s" % (expect_exit_code, exit_code))
                register_exception(error)

        for output_index, output_tuple in enumerate(testdef.outputs):
            # Get the correct hid
            name, outfile, attributes = output_tuple
            output_testdef = bunch.Bunch( name=name, outfile=outfile, attributes=attributes )
            try:
                output_data = data_list[ name ]
            except (TypeError, KeyError):
                # Legacy - fall back on ordered data list access if data_list is
                # just a list (case with twill variant or if output changes its
                # name).
                if hasattr(data_list, "values"):
                    output_data = list(data_list.values())[ output_index ]
                else:
                    output_data = data_list[ len(data_list) - len(testdef.outputs) + output_index ]
            self.assertTrue( output_data is not None )
            try:
                galaxy_interactor.verify_output( history, jobs, output_data, output_testdef=output_testdef, shed_tool_id=shed_tool_id, maxseconds=maxseconds )
            except Exception as e:
                register_exception(e)

        other_checks = {
            "command_line": "Command produced by the job",
            "stdout": "Standard output of the job",
            "stderr": "Standard error of the job",
        }
        for what, description in other_checks.items():
            if getattr( testdef, what, None ) is not None:
                try:
                    data = job_stdio[what]
                    verify_assertions( data, getattr( testdef, what ) )
                except AssertionError as err:
                    errmsg = '%s different than expected\n' % description
                    errmsg += str( err )
                    register_exception( AssertionError( errmsg ) )

        for output_collection_def in testdef.output_collections:
            try:
                name = output_collection_def.name
                # TODO: data_collection_list is clearly a bad name for dictionary.
                if name not in data_collection_list:
                    template = "Failed to find output [%s], tool outputs include [%s]"
                    message = template % (name, ",".join(data_collection_list.keys()))
                    raise AssertionError(message)

                # Data collection returned from submission, elements may have been populated after
                # the job completed so re-hit the API for more information.
                data_collection_returned = data_collection_list[ name ]
                data_collection = galaxy_interactor._get( "dataset_collections/%s" % data_collection_returned[ "id" ], data={"instance_type": "history"} ).json()

                def get_element( elements, id ):
                    for element in elements:
                        if element["element_identifier"] == id:
                            return element
                    return False

                expected_collection_type = output_collection_def.collection_type
                if expected_collection_type:
                    collection_type = data_collection[ "collection_type"]
                    if expected_collection_type != collection_type:
                        template = "Expected output collection [%s] to be of type [%s], was of type [%s]."
                        message = template % (name, expected_collection_type, collection_type)
                        raise AssertionError(message)

                expected_element_count = output_collection_def.count
                if expected_element_count:
                    actual_element_count = len(data_collection[ "elements" ])
                    if expected_element_count != actual_element_count:
                        template = "Expected output collection [%s] to have %s elements, but it had %s."
                        message = template % (name, expected_element_count, actual_element_count)
                        raise AssertionError(message)

                def verify_elements( element_objects, element_tests ):
                    for element_identifier, ( element_outfile, element_attrib ) in element_tests.items():
                        element = get_element( element_objects, element_identifier )
                        if not element:
                            template = "Failed to find identifier [%s] for testing, tool generated collection elements [%s]"
                            message = template % (element_identifier, element_objects)
                            raise AssertionError(message)

                        element_type = element["element_type"]
                        if element_type != "dataset_collection":
                            hda = element[ "object" ]
                            galaxy_interactor.verify_output_dataset(
                                history,
                                hda_id=hda["id"],
                                outfile=element_outfile,
                                attributes=element_attrib,
                                shed_tool_id=shed_tool_id
                            )
                        if element_type == "dataset_collection":
                            elements = element[ "object" ][ "elements" ]
                            verify_elements( elements, element_attrib.get( "elements", {} ) )

                verify_elements( data_collection[ "elements" ], output_collection_def.element_tests )
            except Exception as e:
                register_exception(e)

        if found_exceptions:
            raise JobOutputsError(found_exceptions, job_stdio)
        else:
            return job_stdio


class JobOutputsError(AssertionError):

    def __init__(self, output_exceptions, job_stdio):
        big_message = "\n".join(map(str, output_exceptions))
        super(JobOutputsError, self).__init__(big_message)
        self.job_stdio = job_stdio
        self.output_exceptions = output_exceptions


@nottest
def build_tests( app=None, testing_shed_tools=False, master_api_key=None, user_api_key=None ):
    """
    If the module level variable `toolbox` is set, generate `ToolTestCase`
    classes for all of its tests and put them into this modules globals() so
    they can be discovered by nose.
    """
    if app is None:
        return

    # Push all the toolbox tests to module level
    G = globals()

    # Eliminate all previous tests from G.
    for key, val in G.items():
        if key.startswith( 'TestForTool_' ):
            del G[ key ]
    for i, tool_id in enumerate( app.toolbox.tools_by_id ):
        tool = app.toolbox.get_tool( tool_id )
        if isinstance( tool, TOOL_TYPES_NO_TEST ):
            # We do not test certain types of tools (e.g. Data Manager tools) as part of ToolTestCase
            continue
        if tool.tests:
            shed_tool_id = None if not testing_shed_tools else tool.id
            # Create a new subclass of ToolTestCase, dynamically adding methods
            # named test_tool_XXX that run each test defined in the tool config.
            name = "TestForTool_" + tool.id.replace( ' ', '_' )
            baseclasses = ( ToolTestCase, )
            namespace = dict()
            for j, testdef in enumerate( tool.tests ):
                test_function_name = 'test_tool_%06d' % j

                def make_test_method( td ):
                    def test_tool( self ):
                        self.do_it( td )
                    test_tool.__name__ = test_function_name

                    return test_tool

                test_method = make_test_method( testdef )
                test_method.__doc__ = "%s ( %s ) > %s" % ( tool.name, tool.id, testdef.name )
                namespace[ test_function_name ] = test_method
                namespace[ 'shed_tool_id' ] = shed_tool_id
                namespace[ 'master_api_key' ] = master_api_key
                namespace[ 'user_api_key' ] = user_api_key
            # The new.classobj function returns a new class object, with name name, derived
            # from baseclasses (which should be a tuple of classes) and with namespace dict.
            new_class_obj = new.classobj( name, baseclasses, namespace )
            G[ name ] = new_class_obj
