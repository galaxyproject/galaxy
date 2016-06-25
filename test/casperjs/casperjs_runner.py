"""Test runner for casperjs headless browser tests with the Galaxy distribution.

Allows integration of casperjs tests with run_functional_tests.sh

Tests can be run in any of the following ways:
* casperjs test mytests.js --url='http://localhost:8080'
* python casperjs_runner.py
* nosetests
* sh run_tests.sh -j
* sh run_tests.sh test/casperjs/casperjs_runner.py
* sh run_tests.sh

Note: that you can enable (lots of) debugging info using cli options:
* casperjs test api-user-tests.js --url='http://localhost:8080' --verbose=true --logLevel=debug

(see casperjs.org for more information)

Note: This works with CasperJS 1.1 and PhantomJS 1.9.2 and these libraries seem to break backward
compatibility a lot.

Note: You can pass in extra data using --data='<some JSON object>'
    and it will be available in your script as spaceghost.fixtureData.

    Example using a specific user account:
        casperjs test api-history-tests.js --url="http://localhost:8080" \
            --data='{ "testUser": { "email": "foo@example.com", "password": "123456" } }'
        // ...then, in script:
        spaceghost.user.loginOrRegisterUser(
            spaceghost.fixtureData.testUser.email,
            spaceghost.fixtureData.testUser.password );

    Example of specifing user and admin user credentials:
        casperjs test api-configuration-tests.js --url="http://localhost:8080" \
            --admin='{"email": "foo@example.com", "password": "123456" }' \
"""

import errno
import json
import logging
import os
import re
import subprocess
import sys
import unittest

from server_env import TestEnvironment

# -------------------------------------------------------------------- can't do 2.5

( major, minor, micro, releaselevel, serial ) = sys.version_info
if minor < 6:
    msg = 'casperjs requires python 2.6 or newer. Using: %s' % ( sys.version )
    try:
        # if nose is installed do a skip test
        from nose.plugins.skip import SkipTest
        raise SkipTest( msg )
    except ImportError as i_err:
        raise AssertionError( msg )

# --------------------------------------------------------------------

logging.basicConfig( stream=sys.stderr, name=__name__ )
log = logging.getLogger( __name__ )

# ==================================================================== MODULE VARS
_PATH_TO_HEADLESS = 'casperjs'

_TODO = """
    get data back from js scripts (uploaded files, etc.)
    use returned json to output list of failed assertions if code == 2
    better way to turn debugging on from the environment
"""


# ====================================================================
class HeadlessJSJavascriptError( Exception ):
    """An error that occurrs in the javascript test file.
    """
    pass


class CasperJSTestCase( unittest.TestCase ):
    """Casper tests running in a unittest framework.
    """
    # casper uses a lot of escape codes to colorize output - these capture those and allow removal
    escape_code_compiled_pattern = None
    escape_code_pattern = r'\x1b\[[\d|;]+m'

    # info on where to get casper js - shown when the exec can't be found
    casper_info = """
    CasperJS is a navigation scripting & testing utility for PhantomJS, written in Javascript.
    More information is available at: casperjs.org
    """

    # debugging flag - set to true to have casperjs tests output with --verbose=true and --logLevel=debug
    # debug = True
    debug = False
    # bit of a hack - this is the beginning of the last string when capserjs --verbose=true --logLevel=debug
    #   use this to get subprocess to stop waiting for output
    casper_done_str = '# Stopping'

    # convert js test results to unittest.TestResults
    results_adapter = None  # CasperJsonToUnittestResultsConverter()

    # ---------------------------------------------------------------- run the js script
    def run_js_script( self, rel_script_path, *args, **kwargs ):
        """Start the headless browser tests in a separate process and use both
        the subprocess return code and the stdout output (formatted as JSON)
        to determine which tests failed and which passed.
        """
        log.debug( 'beginning headless browser tests: %s', rel_script_path )
        process_command_list = self.build_command_line( rel_script_path, *args, **kwargs )
        log.debug( 'process_command_list: %s', str( process_command_list ) )
        try:
            process = subprocess.Popen( process_command_list,
                                        shell=False,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE )

            # output from the browser (stderr only) immediately
            while process.poll() is None:
                stderr_msg = process.stderr.readline()
                stderr_msg = self.strip_escape_codes( stderr_msg.strip() )
                if stderr_msg:
                    log.debug( '(%s): %s', rel_script_path, stderr_msg )
                    # HACK: this is the last string displayed using the debug settings - afterwards it hangs
                    #   so: bail on this string
                    if stderr_msg.startswith( self.casper_done_str ):
                        break

            # stdout is assumed to have the json test data/results
            ( stdout_output, stderr_output ) = process.communicate()
            # log.debug( '%s stdout output:\n%s', rel_script_path, stdout_output )
            # log.debug( '%s stderr output:\n%s', rel_script_path, stderr_output )

            log.debug( 'process.returncode: %d', process.returncode )

            # 1.1 has an annoying info bar that happens before it gets to our stuff, so...
            stdout_output = '\n'.join( stdout_output.split( '\n' )[1:] )
            # log.debug( 'stdout_output:\n' + stdout_output )

            if process.returncode == 1:
                # TODO: this is a fail on first effect
                raise self.browser_error_to_exception( rel_script_path, stdout_output )

        # couldn't find the headless browser,
        #   provide information (as it won't be included by default with galaxy)
        except OSError as os_err:
            if os_err.errno == errno.ENOENT:
                log.error( 'No path to headless browser executable: %s\n' +
                           'These tests were designed to use the following headless browser:\n%s',
                           self.exec_path, self.casper_info )
            raise

        return self.handle_js_results( stdout_output )

    def build_command_line( self, rel_script_path, *args, **kwargs ):
        """Build the headless browser command line list for subprocess.
        """
        command_line_list = [ self.exec_path ]

        # as of casperjs 1.1, we always need to use the 'test' command
        command_line_list.append( 'test' )

        # make rel_script_path an absolute path (when this is not run from its dir - i.e. run_tests.sh)
        curr_dir = os.path.dirname( __file__ )
        script_path = os.path.join( curr_dir, rel_script_path )
        command_line_list.append( script_path )

        # let browser know where the server is (from the TestEnvironment created in setUp)
        command_line_list.append( '--url=' + self.env.url )

        # add the return json only option
        #   - has script send normal output to stderr and results, errors, logs to stdout as json
        command_line_list.append( '--return-json' )

        # check flag to output (very) verbose debugging messages from casperjs and tests
        # NOTE: this can be set in the class or by using the debug_these_tests flag in server_env
        if self.debug or ( rel_script_path in self.env.debug_these_tests ):
            command_line_list.extend([ '--verbose=true', '--logLevel=debug' ])
            # TODO: add capture, html output flags

        # TODO: allow casperjs cli options ('--includes='), ?in args, kwargs?
        command_line_list.extend( args )

        # send extra data - encode kwargs as json to pass to casper for decoding
        # as of 1.1, we need to pass this under a opt
        command_line_list.append( '--data=' + json.dumps( kwargs ) )
        return command_line_list

    def strip_escape_codes( self, msg ):
        """Removes colorizing escape codes from casper output strings.
        """
        if not self.escape_code_compiled_pattern:
            self.escape_code_compiled_pattern = re.compile( self.escape_code_pattern )
        return re.sub( self.escape_code_compiled_pattern, '', msg )

    # ---------------------------------------------------------------- convert js error to python error
    def browser_error_to_exception( self, script_path, stdout_output ):
        """Converts the headless' error from JSON into a more informative
        python HeadlessJSJavascriptError.
        """
        try:
            # assume it's json and located in errors (and first)
            js_test_results = json.loads( stdout_output )
            last_error = js_test_results['errors'][0]
            err_string = ( "%s\n%s" % ( last_error['msg'],
                           self.browser_backtrace_to_string( last_error['backtrace'] ) ) )

        # if we couldn't parse json from what's returned on the error, dump stdout
        except ValueError as val_err:
            if str( val_err ) == 'No JSON object could be decoded':
                log.debug( '(error parsing returned JSON from casperjs, dumping stdout...)\n:%s', stdout_output )
                return HeadlessJSJavascriptError( 'see log for details' )
            else:
                raise

        # otherwise, raise a vanilla exc
        except Exception as exc:
            log.debug( '(failed to parse error returned from %s: %s)', _PATH_TO_HEADLESS, str( exc ) )
            return HeadlessJSJavascriptError(
                "ERROR in headless browser script %s" % ( script_path ) )

        # otherwise, raise with msg and backtrace
        return HeadlessJSJavascriptError( err_string )

    def browser_backtrace_to_string( self, backtrace ):
        """Converts list of trace dictionaries (as might be returned from
        json results) to a string similar to a python backtrace.
        """
        template = '  File "%s", line %s, in %s'
        traces = []
        for trace in backtrace:
            traces.append( template % ( trace[ 'file' ], trace[ 'line' ], trace[ 'function' ] ) )
        return '\n'.join( traces )

    # ---------------------------------------------------------------- results
    def handle_js_results( self, results ):
        """Handle the results of the js tests by either converting them
        with the results adapter or checking for a failure list.
        """

        # if given an adapter - use it
        if self.results_adapter:
            self.results_adapter.convert( results, self )

        # - otherwise, assert no failures found
        else:
            js_test_results = json.loads( results )
            failures = js_test_results[ 'failures' ]
            assert len( failures ) == 0, (
                "%d assertions failed in the headless browser tests" % ( len( failures ) ) +
                " (see the log for details)" )

    # ---------------------------------------------------------------- TestCase overrides
    def setUp( self ):
        # set up the env for each test
        self.env = TestEnvironment.instance()
        self.exec_path = _PATH_TO_HEADLESS

    def run( self, result=None ):
        # wrap this in order to save ref to result
        # TODO: gotta be a better way
        self.result = result
        unittest.TestCase.run( self, result=result )


# ==================================================================== RESULTS CONVERSION
class CasperJsonToUnittestResultsConverter( object ):
    """Convert casper failures, success to individual unittest.TestResults
    """
    # TODO: So far I can add result instances - but each has the id, shortDescription
    #   of the TestCase.testMethod that called it. Can't find out how to change these.

    def convert( self, json_results, test ):
        """Converts JSON test results into unittest.TestResults.

        precondition: test should have attribute 'result' which
        is a unittest.TestResult (for that test).
        """
        results_dict = json.loads( json_results )
        failures = results_dict[ 'testResults' ][ 'failures' ]
        passes = results_dict[ 'testResults' ][ 'passes' ]
        self.add_json_failures_to_results( failures, test )
        self.add_json_successes_to_results( passes, test )

    def add_json_failures_to_results( self, failures, test ):
        """Converts JSON test failures.
        """
        # precondition: result should be an attr of test (a TestResult)
        # TODO: no way to change test.desc, name in output?
        for failure in failures:
            # TODO: doesn't change shortDescription
            # if 'standard' in failure:
            #    self.__doc__ = failure[ 'standard' ]
            test.result.addFailure( test, self.casper_failure_to_unittest_failure( failure ) )
            test.result.testsRun += 1

    def casper_failure_to_unittest_failure( self, casper_failure, failure_class=AssertionError ):
        """Returns a casper test failure (in dictionary form) as a 3-tuple of
        the form used by unittest.TestResult.addFailure.

        Used to add failures to a casperjs TestCase.
        """
        # TODO: this is all too elaborate
        fail_type = casper_failure[ 'type' ]
        values = json.dumps( casper_failure[ 'values' ] )
        desc = casper_failure[ 'standard' ]
        if 'messgae' in casper_failure:
            desc = casper_failure[ 'message' ]
        failure_msg = "(%s) %s: %s" % ( fail_type, desc, values )
        # TODO: tb is empty ([]) - can we get file info from casper, covert to py trace?
        return ( failure_class, failure_msg, [] )

    def add_json_successes_to_results( self, successes, test ):
        """Converts JSON test successes.
        """
        for success in successes:
            # attempt to re-write test result description - doesn't work
            # if 'standard' in success:
            #    self.__doc__ = success[ 'standard' ]
            test.result.addSuccess( test )
            test.result.testsRun += 1


# ==================================================================== MODULE FIXTURE
# NOTE: nose will run these automatically
def setup_module():
    log.debug( '\n--------------- setting up module' )


def teardown_module():
    log.debug( '\n--------------- tearing down module' )


test_user = {
    'email': 'test1@test.test',
    'password': '123456'
}


# ==================================================================== TESTCASE EXAMPLE
# these could be broken out into other py files - shouldn't be necc. ATM
class Test_01_User( CasperJSTestCase ):
    """Tests for the Galaxy user centered functionality:
    registration, login, etc.
    """
    def test_10_registration( self ):
        """User registration tests:
        register new user, logout, attempt bad registrations.
        """
        # all keywords will be compiled into a single JSON obj and passed to the server
        # self.run_js_script( 'registration-tests.js',
        #    testUser=test_user )
        #    # this causes a time out in history-panel-tests: why?
        #    # also: I can't seem to bump the timeout to an error (using a handler) - causes script to hang
        #    #   removing for the sake of bbot
        self.run_js_script( 'registration-tests.js' )

        # TODO:?? could theoretically do db cleanup, checks here with SQLALX
        # TODO: have run_js_script return other persistent fixture data (uploaded files, etc.)

    def test_20_login( self ):
        """User log in tests.
        """
        self.run_js_script( 'login-tests.js' )


class Test_02_Tools( CasperJSTestCase ):
    """(Minimal) casperjs tests for tools.
    """
    def test_10_upload( self ):
        """Tests uploading files
        """
        self.run_js_script( 'upload-tests.js' )


class Test_03_HistoryPanel( CasperJSTestCase ):
    """Tests for History fetching, rendering, and modeling.
    """
    def test_00_history_panel( self ):
        """Test history panel basics (controls, structure, refresh, history options menu, etc.).
        """
        self.run_js_script( 'history-panel-tests.js' )

    def test_10_history_options( self ):
        """Test history options button.
        """
        self.run_js_script( 'history-options-tests.js' )

    def test_20_anonymous_histories( self ):
        """Test history panel basics with an anonymous user.
        """
        self.run_js_script( 'anon-history-tests.js' )


class Test_04_HDAs( CasperJSTestCase ):
    """Tests for HistoryDatasetAssociation fetching, rendering, and modeling.
    """
    def test_00_HDA_states( self ):
        """Test structure rendering of HDAs in all the possible HDA states
        """
        self.run_js_script( 'hda-state-tests.js' )


class Test_05_API( CasperJSTestCase ):
    """Tests for API functionality and security.
    """
    def test_00_history_api( self ):
        """Test history API.
        """
        self.run_js_script( 'api-history-tests.js' )

    def test_01_hda_api( self ):
        """Test HDA API.
        """
        self.run_js_script( 'api-hda-tests.js' )

    def test_02_history_permissions_api( self ):
        """Test API permissions for importable, published histories.
        """
        self.run_js_script( 'api-history-permission-tests.js' )

    def test_03_anon_history_api( self ):
        """Test API for histories using anonymous user.
        """
        self.run_js_script( 'api-anon-history-tests.js' )

    def test_04_anon_history_permissions_api( self ):
        """Test API permissions for importable, published histories using anonymous user.
        """
        self.run_js_script( 'api-anon-history-permission-tests.js' )

    def test_06_visualization_api( self ):
        """Test API for visualizations.
        """
        self.run_js_script( 'api-visualizations-tests.js' )

    def test_07_tools_api( self ):
        """Test API for tools.
        """
        self.run_js_script( 'api-tool-tests.js' )

    def test_08_configuration_api( self ):
        """Test API for configuration.
        """
        self.run_js_script( 'api-configuration-tests.js' )

    def test_09_user_api( self ):
        """Test API for users.
        """
        self.run_js_script( 'api-user-tests.js' )


# ==================================================================== MAIN
if __name__ == '__main__':
    log.setLevel( logging.DEBUG )
    from server_env import log as server_env_log
    server_env_log.setLevel( logging.DEBUG )
    setup_module()
    # TODO: server_env config doesn't work with unittest's lame main fn
    unittest.main()
    # teardown_module() isn't called when unittest.main is used
