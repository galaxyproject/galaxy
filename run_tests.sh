#!/bin/bash

cd "$(dirname "$0")"

show_help() {
cat <<EOF
'${0##*/} -api (test_path)'         for running all the test scripts in the ./lib/galaxy_test/api directory, test_path
                                    can be pytest selector
'${0##*/} -cwl (test_path)'         for running all the test scripts in the ./lib/galaxy_test/api/cwl directory, test_path
                                    can be pytest selector
'${0##*/} -integration (test_path)' for running all integration test scripts in the ./test/integration directory, test_path
                                    can be pytest selector
'${0##*/} -toolshed (test_path)'    for running all the test scripts in the ./lib/tool_shed/test directory
'${0##*/} -main'                    for running tests of tools shipped with Galaxy
'${0##*/} -framework'               for running through example tool tests testing framework features in test/functional/tools"
'${0##*/} -framework -id toolid'    for testing one framework tool (in test/functional/tools/) with id 'toolid'
'${0##*/} -framework-workflows'      for running through workflow tests to test correctness of workflow evaluation
'${0##*/} -framework-workflows -id workflow_name' test single workflow framework test
'${0##*/} -data_managers -id data_manager_id'    for testing one Data Manager with id 'data_manager_id'
'${0##*/} -unit'                    for running all unit tests (doctests and tests in test/unit)
'${0##*/} -unit (test_selector)'    for running unit tests on specified test path (using pytest selector syntax)
'${0##*/} -selenium'                for running all selenium web tests (in lib/galaxy_test/selenium)
'${0##*/} -selenium (test_selector)' for running specified selenium web tests (using pytest selector syntax)

This wrapper script largely serves as a point documentation and convenience for
running Galaxy's Python tests. All Python tests shipped with Galaxy can be run with
pytest directly. Galaxy's client unit tests can be run with ``make client-test``
or ``yarn`` directly as documented in detail in ``client/README.md``.

The main test types are as follows:

- API: These tests are located in lib/galaxy_test/api and test various aspects of the Galaxy
   API and test general backend aspects of Galaxy using the API.
- Integration: These tests are located in test/integration and test special
   configurations of Galaxy. All API tests assume a particular Galaxy configuration
   defined by test/base/driver_util.py and integration tests can be used to
   launch and test Galaxy in other configurations.
- Framework: These tests are all Galaxy tool tests and can be found in
   test/functional/tools. These are for the most part meant to test and
   demonstrate features of the tool evaluation environment and of Galaxy tool XML
   files.
- Unit: These are Python unit tests either defined as doctests or inside of
   test/unit. These should generally not require a Galaxy instance and should
   quickly test just a component or a few components of Galaxy's backend code.
- Selenium: These are full stack tests meant to test the Galaxy UI with real
   browsers and are located in lib/galaxy_test/selenium.
- ToolShed: These are web tests that use the older Python web testing
   framework twill to test ToolShed related functionality. These are
   located in lib/tool_shed/test.

Python testing is done via pytest. Specific tests can be selected
using the syntax described at https://docs.pytest.org/en/latest/how-to/usage.html .
A few examples are shown below.

Run all API tests:
    ./run_tests.sh -api

The same test as above can be run using pytest directly as follows:
    pytest lib/galaxy_test/api

However, when using pytest directly, output options defined in this
file aren't respected and a new Galaxy instance will be created for each
Test class (this scripts optimizes it so all tests can share a Galaxy
instance).

Run a full class of API tests:
    ./run_tests.sh -api lib/galaxy_test/api/test_tools.py::TestToolsApi

Run a specific API test:
    ./run_tests.sh -api lib/galaxy_test/api/test_tools.py::TestToolsApi::test_map_over_with_output_format_actions

Run all selenium tests (Under Linux using Docker):
    # Start selenium chrome Docker container
    docker run -d -p 4444:4444 -v /dev/shm:/dev/shm selenium/standalone-chrome:3.0.1-aluminum
    GALAXY_TEST_SELENIUM_REMOTE=1 ./run_tests.sh -selenium

Run a specific selenium test (under Linux or Mac OS X after installing geckodriver or chromedriver):
    ./run_tests.sh -selenium lib/galaxy_test/selenium/test_registration.py::TestRegistration::test_reregister_username_fails

Run a selenium test against a running server while watching client (fastest iterating on client tests):
    ./run.sh & # run Galaxy on 8080
    make client-watch & # watch for client changes
    export GALAXY_TEST_EXTERNAL=http://localhost:8080/  # Target tests at server.
    . .venv/bin/activate # source the virtualenv so can skip run_tests.sh.
    pytest lib/galaxy_test/selenium/test_workflow_editor.py::TestWorkflowEditor::test_data_input

To run the tool tests for a specific framework test tool
listed in test/functional/tools/sample_tool_conf.xml.

    ./run_tests.sh -framework -id <tool_id>

If you'd like to skip this script and run it with pytest
directly a command like the following can be used. Note
the framework tools run with conda installation on but 99%
of the tools do not require this so this example includes
disabling that.

    GALAXY_TEST_TOOL_CONF="test/functional/tools/sample_tool_conf.xml" GALAXY_CONFIG_OVERRIDE_CONDA_AUTO_INIT=false pytest test/functional/test_toolbox_pytest.py -k <tool_id> -m tool

Note About Selenium Tests:

If using a local selenium driver such as a Chrome or Firefox based one
either chromedriver or geckodriver needs to be installed an placed on
the PATH.

More information on geckodriver can be found at
https://github.com/mozilla/geckodriver and more information on
chromedriver can be found at
https://sites.google.com/chromium.org/driver/ .

By default Galaxy will check the PATH for these and pick
whichever it finds. This can be overridden by setting
GALAXY_TEST_SELENIUM_BROWSER to either FIREFOX, CHROME, or something
more esoteric (including OPERA).

If PyVirtualDisplay is installed Galaxy will attempt to run this
browser in a headless mode. This can be disabled by setting
GALAXY_TEST_SELENIUM_HEADLESS to 0 however.

Selenium can also be setup a remote service - to target a service set
GALAXY_TEST_SELENIUM_REMOTE to 1. The target service may be configured
with GALAXY_TEST_SELENIUM_REMOTE_PORT and
GALAXY_TEST_SELENIUM_REMOTE_HOST. By default Galaxy will assume the
remote service being targetted is CHROME - but this can be overridden
with GALAXY_TEST_SELENIUM_BROWSER.

In this remote mode, please ensure that GALAXY_TEST_HOST is set to a
host that is accessible from the Selenium host. By default under Linux
if GALAXY_TEST_SELENIUM_REMOTE is set, Galaxy will set this to be the IP
address Docker exposes localhost on to its child containers. This trick
doesn't work on Mac OS X and so GALAXY_TEST_HOST will need to be crafted
carefully ahead of time.

For Selenium test cases a stack trace is usually insufficient to diagnose
problems. For this reason, GALAXY_TEST_ERRORS_DIRECTORY is populated with
a new directory of information for each failing test case. This information
includes a screenshot, a stack trace, and the DOM of the currently rendered
Galaxy instance. The new directories are created with names that include
information about the failed test method name and the timestamp. By default,
GALAXY_TEST_ERRORS_DIRECTORY will be set to database/errors.

The Selenium tests seem to be subject to transient failures at a higher
rate than the rest of the tests in Galaxy. Though this is unfortunate,
they have more moving pieces so this is perhaps not surprising. One can
set the GALAXY_TEST_SELENIUM_RETRIES to a number greater than 0 to
automatically retry every failed test case the specified number of times.

External Tests:

A small subset of tests can be run against an existing Galaxy
instance. The external Galaxy instance URL can be configured with
--external_url. If this is set, either --external_master_key or
--external_user_key must be set as well - more tests can be executed
with --external_master_key than with a user key.

Extra options:

 --verbose_errors      Force some tests produce more verbose error reporting.
 --no_cleanup          Do not delete temp files for Python functional tests
                       (-toolshed, -framework, etc...)
 --coverage            Generate a test coverage report. This option currently
                       works with every Python test, but the
                       results may not be reliable with Selenium or other
                       frameworks that primarily test the client.
 --debug               On python test error or failure invoke a pdb shell for
                       interactive debugging of the test
 --report_file         Path of HTML report to produce (for Python Galaxy
                       functional tests). If not given, a default filename will
                       be used, and reported on stderr at the end of the run.
 --xunit_report_file   Path of XUnit report to produce (for Python Galaxy
                       functional tests).
 --skip-venv           Do not create .venv (passes this flag to
                       common_startup.sh)
 --external_url        External URL to use for Galaxy testing (only certain
                       tests).
 --external_master_key Master API key used to configure external tests.
 --external_user_key   User API used for external tests - not required if
                       external_master_key is specified.
  --skip_flakey_fails  Skip flakey tests on error (sets
                       GALAXY_TEST_SKIP_FLAKEY_TESTS_ON_ERROR=1).

Environment Variables:

In addition to the above command-line options, many environment variables
can be used to control the Galaxy functional testing processing. Command-line
options above like (--external_url) will set environment variables - in such
cases the command line argument takes precedent over environment variables set
at the time of running this script.

General Test Environment Variables

GALAXY_TEST_COVERAGE            If set, it is equivalent to passing the
                                --coverage option.

Functional Test Environment Variables

GALAXY_TEST_DBURI               Database connection string used for functional
                                test database for Galaxy.
GALAXY_TEST_INSTALL_DBURI       Database connection string used for functional
                                test database for Galaxy's install framework.
GALAXY_TEST_INSTALL_DB_MERGED   Set to use same database for Galaxy and install
                                framework, this defaults to True for Galaxy
                                tests an False for shed tests.
GALAXY_TEST_DB_TEMPLATE         If GALAXY_TEST_DBURI is unset, this URL can be
                                retrieved and should be an sqlite database that
                                will be upgraded and tested against.
GALAXY_TEST_TMP_DIR             Temp directory used for files required by
                                Galaxy server setup for Galaxy functional tests.
GALAXY_TEST_SAVE                Location to save certain test files (such as
                                tool outputs).
GALAXY_TEST_EXTERNAL            Target an external Galaxy as part of testing.
GALAXY_TEST_JOB_CONFIG_FILE     Job config file to use for the test.
GALAXY_CONFIG_MASTER_API_KEY    Master or admin API key to use as part of
                                testing with GALAXY_TEST_EXTERNAL.
GALAXY_TEST_USER_API_KEY        User API key to use as part of testing with
                                GALAXY_TEST_EXTERNAL.
GALAXY_TEST_VERBOSE_ERRORS      Enable more verbose errors during API tests.
GALAXY_TEST_UPLOAD_ASYNC        Upload tool test inputs asynchronously (may
                                overwhelm sqlite database).
GALAXY_TEST_RAW_DIFF            Don't slice up tool test diffs to keep output
                                managable - print all output. (default off)
GALAXY_TEST_DEFAULT_WAIT        Max time allowed for a tool test before Galaxy
                                gives up (default 86400) - tools may define a
                                maxseconds attribute to extend this.
GALAXY_TEST_TOOL_DEPENDENCY_DIR tool dependency dir to use for Galaxy during
                                functional tests.
GALAXY_TEST_FILE_DIR            Test data sources (default to
              test-data,https://github.com/galaxyproject/galaxy-test-data.git)
GALAXY_TEST_DIRECTORY           $GALAXY_ROOT/test
GALAXY_TEST_TOOL_DATA_PATH      Set to override tool data path during tool
                                shed tests.
GALAXY_TEST_FETCH_DATA          Fetch remote test data to
                                GALAXY_TEST_DATA_REPO_CACHE as part of tool
                                tests if it is not available locally (default
                                to True). Requires git to be available on the
                                command-line.
GALAXY_TEST_DATA_REPO_CACHE     Where to cache remote test data to (default to
                                test-data-cache).
GALAXY_TEST_SKIP_FLAKEY_TESTS_ON_ERROR
                                Skip tests annotated with @flakey on test errors.
HTTP_ACCEPT_LANGUAGE            Defaults to 'en'
GALAXY_TEST_NO_CLEANUP          Do not cleanup main test directory after tests,
                                the deprecated option TOOL_SHED_TEST_NO_CLEANUP
                                does the same thing.
GALAXY_TEST_HOST                Host to use for Galaxy server setup for
                                testing.
GALAXY_TEST_PORT                Port to use for Galaxy server setup for
                                testing.
GALAXY_TEST_TOOL_PATH           Path defaulting to 'tools'.
GALAXY_TEST_SHED_TOOL_CONF      Shed toolbox conf (defaults to
                                config/shed_tool_conf.xml) used when testing
                                installed to tools with -installed.
GALAXY_TEST_HISTORY_ID          Some tests can target existing history ids, this option
                                is fairly limited and not compatible with parallel testing
                                so should be limited to debugging one-off tests.
TOOL_SHED_TEST_HOST             Host to use for shed server setup for testing.
TOOL_SHED_TEST_PORT             Port to use for shed server setup for testing.
TOOL_SHED_TEST_FILE_DIR         Defaults to lib/tool_shed/test/test_data.
TOOL_SHED_TEST_TMP_DIR          Defaults to random /tmp directory - place for
                                tool shed test server files to be placed.
TOOL_SHED_TEST_OMIT_GALAXY      Do not launch a Galaxy server for tool shed
                                testing.
GALAXY_TEST_DISABLE_ACCESS_LOG  Do not log access messages
GALAXY_TEST_AXE_SCRIPT_URL      URL of aXe script to use for accessibility testing.
GALAXY_TEST_SKIP_AXE            Set this to '1' to skip aXe accessibilty testing when
                                running selenium tests.

We're tyring annotate API and Selenium tests with the resources they require
and create to make them more appropriate to run on established Galaxy instances.
The following variables can be used to disable certain classes of properly tests.

GALAXY_TEST_SKIP_IF_REQUIRES_ADMIN
GALAXY_TEST_SKIP_IF_REQUIRES_NEW_HISTORY
GALAXY_TEST_SKIP_IF_REQUIRES_NEW_LIBRARY
GALAXY_TEST_SKIP_IF_REQUIRES_NEW_USER
GALAXY_TEST_SKIP_IF_REQUIRES_NEW_PUBLISHED_OBJECTS
EOF
}

show_list() {
    python tool_list.py
    echo "==========================================================================================================================================="
    echo "'${0##*/} -id bbb'               for testing one tool with id 'bbb' ('bbb' is the tool id)"
    echo "'${0##*/} -sid ccc'              for testing one section with sid 'ccc' ('ccc' is the string after 'section::')"
}

exists() {
    type "$1" >/dev/null 2>/dev/null
}

debug=""
test_script="pytest"
report_file="run_functional_tests.html"
if [ -n "$GALAXY_TEST_COVERAGE" ]; then
    coverage_arg="--with-coverage"
else
    coverage_arg=""
fi
xunit_report_file=""
structured_data_report_file=""
structured_data_html=0
SKIP_CLIENT_BUILD=${GALAXY_SKIP_CLIENT_BUILD:-1}
if [ "$SKIP_CLIENT_BUILD" = "1" ]; then
    skip_client_build="--skip-client-build"
else
    skip_client_build=""
fi

# If in Jenkins environment, create xunit-${BUILD_NUMBER}.xml by default.
if [ -n "$BUILD_NUMBER" ]; then
    xunit_report_file="xunit-${BUILD_NUMBER}.xml"
fi

# Loop through and consume the main arguments.
# Some loops will consume more than one argument (there are extra "shift"s in some cases).
while :
do
    case "$1" in
      -h|--help|-\?)
          show_help
          exit 0
          ;;
      -id|--id)
          if [ $# -gt 1 ]; then
              test_id=$2
              shift 2
          else
              echo "ERROR: --id requires an argument" 1>&2
              exit 1
          fi
          ;;
      -a|-api|--api)
          GALAXY_TEST_USE_HIERARCHICAL_OBJECT_STORE="True"  # Run these tests with a non-trivial object store.
          export GALAXY_TEST_USE_HIERARCHICAL_OBJECT_STORE
          GALAXY_TEST_TOOL_CONF="lib/galaxy/config/sample/tool_conf.xml.sample,test/functional/tools/sample_tool_conf.xml"
          marker="not cwl_conformance"
          report_file="./run_api_tests.html"
          if [ $# -gt 1 ]; then
              api_script=$2
              shift 2
          else
              api_script="./lib/galaxy_test/api"
              shift 1
          fi
          ;;
      -cwl|--cwl)
          GALAXY_TEST_USE_HIERARCHICAL_OBJECT_STORE="True"  # Run these tests with a non-trivial object store.
          export GALAXY_TEST_USE_HIERARCHICAL_OBJECT_STORE
          GALAXY_TEST_TOOL_CONF="lib/galaxy/config/sample/tool_conf.xml.sample,test/functional/tools/sample_tool_conf.xml"
          marker="cwl_conformance"
          report_file="./run_cwl_tests.html"
          generate_cwl_conformance_tests=1
          if [ $# -gt 1 ]; then
              api_script=$2
              shift 2
          else
              api_script="./lib/galaxy_test/api/cwl"
              shift 1
          fi
          ;;
      -selenium|--selenium)
          GALAXY_TEST_TOOL_CONF="lib/galaxy/config/sample/tool_conf.xml.sample,test/functional/tools/sample_tool_conf.xml"
          report_file="./run_selenium_tests.html"
          skip_client_build=""
          if [ $# -gt 1 ]; then
              selenium_script=$2
              shift 2
          else
              selenium_script="./lib/galaxy_test/selenium"
              shift 1
          fi
          ;;
      -t|-toolshed|--toolshed)
          report_file="run_toolshed_tests.html"
          if [ $# -gt 1 ]; then
              toolshed_script=$2
              shift 2
          else
              toolshed_script="./lib/tool_shed/test/functional"
              shift 1
          fi
          ;;
      -clean_pyc|--clean_pyc)
          find lib -iname '*pyc' -exec rm -rf {} \;
          find test -iname '*pyc' -exec rm -rf {} \;
          shift
          ;;
      -skip_flakey_fails|--skip_flakey_fails)
          GALAXY_TEST_SKIP_FLAKEY_TESTS_ON_ERROR=1
          export GALAXY_TEST_SKIP_FLAKEY_TESTS_ON_ERROR
          shift
          ;;
      --external_url)
          export GALAXY_TEST_EXTERNAL=$2
          shift 2
          ;;
      --external_master_key)
          export GALAXY_CONFIG_MASTER_API_KEY=$2
          shift 2
          ;;
      --external_user_key)
          export GALAXY_TEST_USER_API_KEY=$2
          shift 2
          ;;
      -f|-framework|--framework|--framework-tools)
          GALAXY_TEST_TOOL_CONF="test/functional/tools/sample_tool_conf.xml"
          marker="tool"
          report_file="run_framework_tests.html"
          framework_test=1
          shift 1
          ;;
      -w|--framework-workflows)
          marker="workflow"
          report_file="run_framework_workflows_tests.html"
          framework_workflows_test=1
          shift 1
          ;;
      -d|-data_managers|--data_managers)
          marker="data_manager"
          report_file="run_data_managers_tests.html"
          data_managers_test=1
          shift 1
          ;;
      -main|-main_tools|--main_tools)
          GALAXY_TEST_TOOL_CONF="lib/galaxy/config/sample/tool_conf.xml.sample"
          marker="tool"
          report_file="run_framework_tests.html"
          framework_test=1
          shift 1
          ;;
      -r|--report_file)
          if [ $# -gt 1 ]; then
              report_file=$2
              shift 2
          else
              echo "ERROR: --report_file requires an argument" 1>&2
              exit 1
          fi
          ;;
      --xunit_report_file)
          if [ $# -gt 1 ]; then
              xunit_report_file=$2
              shift 2
          else
              echo "ERROR: --xunit_report_file requires an argument" 1>&2
              exit 1
          fi
          ;;
      --structured_data_report_file)
          if [ $# -gt 1 ]; then
              structured_data_report_file=$2
              shift 2
          else
              echo "ERROR: --structured_data_report_file requires an argument" 1>&2
              exit 1
          fi
          ;;
      --structured_data_html)
          structured_data_html=1
          shift
          ;;
      --verbose_errors)
          GALAXY_TEST_VERBOSE_ERRORS=True
          export GALAXY_TEST_VERBOSE_ERRORS
          shift
          ;;
      --ci_test_metrics)
          GALAXY_CONFIG_OVERRIDE_STATSD_PREFIX="galaxy"
          export GALAXY_CONFIG_OVERRIDE_STATSD_PREFIX
          GALAXY_CONFIG_OVERRIDE_STATSD_HOST="localhost"
          export GALAXY_CONFIG_OVERRIDE_STATSD_HOST
          GALAXY_CONFIG_OVERRIDE_STATSD_INFLUXDB="true"
          export GALAXY_CONFIG_OVERRIDE_STATSD_INFLUXDB
          GALAXY_CONFIG_OVERRIDE_DATABASE_LOG_QUERY_COUNTS="true"
          export GALAXY_CONFIG_OVERRIDE_DATABASE_LOG_QUERY_COUNTS
          GALAXY_CONFIG_OVERRIDE_ENABLE_PER_REQUEST_SQL_DEBUGGING="true"
          export GALAXY_CONFIG_OVERRIDE_ENABLE_PER_REQUEST_SQL_DEBUGGING
          GALAXY_CONFIG_OVERRIDE_STATSD_MOCK_CALLS="true"
          export GALAXY_CONFIG_OVERRIDE_STATSD_MOCK_CALLS
          shift
          ;;
      -c|--coverage)
          # Must have coverage installed (try `which coverage`) - only works with pytest
          # for now. Would be great to get this to work with functional tests though.
          coverage_arg="--with-coverage"
          shift
          ;;
      --debug)
          debug="--pdb"
          shift
          ;;
      -u|-unit|--unit)
          report_file="run_unit_tests.html"
          unit_extra='--doctest-modules
			--ignore lib/galaxy/jobs/runners/chronos.py
			--ignore lib/galaxy/model/migrations/alembic
			--ignore lib/galaxy/tools/bundled
			--ignore lib/galaxy/web/proxy/js/node_modules/
			--ignore lib/galaxy_test
			--ignore lib/tool_shed/test
			--ignore lib/tool_shed/webapp/controllers
			--ignore=lib/tool_shed/webapp/model/migrations/alembic/'
          generate_cwl_conformance_tests=1
          if [ $# -gt 1 ]; then
              unit_extra="$unit_extra $2"
              shift 2
          else
              unit_extra="$unit_extra lib test/unit"
              shift 1
          fi
          ;;
      -i|-integration|--integration)
          GALAXY_TEST_TOOL_CONF="lib/galaxy/config/sample/tool_conf.xml.sample,test/functional/tools/sample_tool_conf.xml"
          report_file="./run_integration_tests.html"
          if [ $# -gt 1 ]; then
              integration_extra=$2
              shift 2
          else
              integration_extra="./test/integration"
              shift 1
          fi
          ;;
      --no_cleanup)
          GALAXY_TEST_NO_CLEANUP=1
          export GALAXY_TEST_NO_CLEANUP
          TOOL_SHED_TEST_NO_CLEANUP=1
          export TOOL_SHED_TEST_NO_CLEANUP
          GALAXY_INSTALL_TEST_NO_CLEANUP=1
          export GALAXY_INSTALL_TEST_NO_CLEANUP
          echo "Skipping Python test clean up."
          shift
          ;;
      --skip-venv)
          skip_venv='--skip-venv'
          shift
          ;;
      --no-create-venv)
          no_create_venv='--no-create-venv'
          shift
          ;;
      --no-replace-pip|--replace-pip)
          # Deprecated options
          shift
          ;;
      --skip-common-startup)
          # Don't run ./scripts/common_startup.sh (presumably it has already
          # been done, or you know what you're doing).
          skip_common_startup=1
          shift
          ;;
      --)
          # Do not default to running the functional tests in this case, caller
          # is opting to run specific tests so don't interfere with that by default.
          shift
          break
          ;;
      -*)
          echo "ERROR: Invalid option $1" 1>&2
          show_help
          exit 1
          ;;
      *)
          if [ -n "$1" ]; then
            test_target="$1"
            shift
          fi
          # Maybe we shouldn't break here but for now to pass more than one argument to the
          # underlying test driver use -- instead.
          break
          ;;
    esac
done

if [ -z "$skip_common_startup" ]; then
    if [ -n "$GALAXY_TEST_DBURI" ]; then
            GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION=$GALAXY_TEST_DBURI
            export GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION
    fi
    ./scripts/common_startup.sh $skip_venv $no_create_venv $skip_client_build --dev-wheels || exit 1
    unset GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION
fi

. ./scripts/common_startup_functions.sh

setup_python

if [ -n "$framework_test" ] || [ -n "$data_managers_test" ] ; then
    if [ -n "$test_id" ]; then
        selector="-k $test_id"
    else
        selector=""
    fi
    extra_args="test/functional/test_toolbox_pytest.py $selector"
elif [ -n "$framework_workflows_test" ]; then
    if [ -n "$test_id" ]; then
        selector="-k $test_id"
    else
        selector=""
    fi
    extra_args="lib/galaxy_test/workflow/tests.py $selector"
elif [ -n "$selenium_script" ]; then
    extra_args="$selenium_script"
elif [ -n "$toolshed_script" ]; then
    extra_args="$toolshed_script"
elif [ -n "$api_script" ]; then
    extra_args="$api_script"
elif [ -n "$unit_extra" ]; then
    extra_args="$unit_extra"
elif [ -n "$integration_extra" ]; then
    extra_args="$integration_extra"
elif [ -n "$test_target" ] ; then
    extra_args="$test_target"
else
    echo "ERROR: No testing mode selected!" 1>&2
    show_help
    exit 1
fi

if [ -n "$xunit_report_file" ]; then
    xunit_args="--junit-xml $xunit_report_file"
else
    xunit_args=""
fi
if [ -n "$structured_data_report_file" ]; then
    structured_data_args="--json-report --json-report-file $structured_data_report_file"
else
    structured_data_args=""
fi
if [ -n "$generate_cwl_conformance_tests" ]; then
    make generate-cwl-conformance-tests
fi
export GALAXY_TEST_TOOL_CONF
if [ "$coverage_arg" = '--with-coverage' ]; then
    coverage_arg="--cov-report xml --cov-report term --cov=lib"
fi
if [ -n "$marker" ]; then
    marker_args=(-m "$marker")
else
    marker_args=()
fi
args=(-v $debug $structured_data_args --html "$report_file" --self-contained-html $coverage_arg $xunit_args $extra_args "${marker_args[@]}" "$@")
"$test_script" "${args[@]}"
exit_status=$?
echo "Testing complete. HTML report is in \"$report_file\"." 1>&2
if [ "$structured_data_html" = '1' ]; then
   python scripts/tests_markdown.py --output_path "${structured_data_report_file%.json}.html" "$structured_data_report_file"
fi
exit ${exit_status}
