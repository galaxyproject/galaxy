#!/bin/sh

pwd_dir=$(pwd)
cd `dirname $0`

# A good place to look for nose info: http://somethingaboutorange.com/mrl/projects/nose/
rm -f run_functional_tests.log

show_help() {
cat <<EOF
'${0##*/} -id bbb'                  for testing one tool with id 'bbb' ('bbb' is the tool id)
'${0##*/} -sid ccc'                 for testing one section with sid 'ccc' ('ccc' is the string after 'section::')
'${0##*/} -list'                    for listing all the tool ids
'${0##*/} -api (test_path)'         for running all the test scripts in the ./test/api directory
'${0##*/} -toolshed (test_path)'    for running all the test scripts in the ./test/shed_functional/functional directory
'${0##*/} -installed'               for running tests of Tool Shed installed tools
'${0##*/} -framework'               for running through example tool tests testing framework features in test/functional/tools"
'${0##*/} -framework -id toolid'    for testing one framework tool (in test/functional/tools/) with id 'toolid'
'${0##*/} -data_managers -id data_manager_id'    for testing one Data Manager with id 'data_manager_id'
'${0##*/} -unit'                    for running all unit tests (doctests and tests in test/unit)
'${0##*/} -unit (test_path)'        for running unit tests on specified test path
'${0##*/} -qunit'                   for running qunit JavaScript tests
'${0##*/} -qunit testname'          for running single JavaScript test with given name
'${0##*/} -selenium'                for running all selenium web tests (in test/selenium_tests)
'${0##*/} -selenium (test_path)'    for running specified selenium web tests (use nosetest path)

This wrapper script largely serves as a point documentation and convenience -
most tests shipped with Galaxy can be run with nosetests or qunit directly.

The main test types are as follows:

- API: These tests are located in test/api and test various aspects of the Galaxy
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
- QUnit: These are JavaScript unit tests defined in test/qunit.
- Selenium: These are full stack tests meant to test the Galaxy UI with real
   browsers and are located in test/selenium_tests.
- ToolShed: These are web tests that use the older Python web testing
   framework twill to test ToolShed related functionality. These are
   located in test/shed_functional.

Nose tests will allow specific tests to be selected per the documentation at
https://nose.readthedocs.org/en/latest/usage.html#selecting-tests.  These are
indicated with the optional parameter (test_path).  A few examples are:

Run all API tests:
    ./run_tests.sh -api

The same test as above can be run using nosetests directly as follows:
    nosetests test/api

However when using nosetests directly output options defined in this
file aren't respected and a new Galaxy instance will be created for each
TestCase class (this scripts optimizes it so all tests can share a Galaxy
instance).

Run a full class of API tests:
    ./run_tests.sh -api test/api/test_tools.py:ToolsTestCase

Run a specific API test:
    ./run_tests.sh -api test/api/test_tools.py:ToolsTestCase.test_map_over_with_output_format_actions

Run all selenium tests (Under Linux using Docker):
    # Start selenium chrome Docker container
    docker run -d -p 4444:4444 -v /dev/shm:/dev/shm selenium/standalone-chrome:3.0.1-aluminum
    GALAXY_TEST_SELENIUM_REMOTE=1 ./run_tests.sh -selenium

Run a specific selenium test (under Linux or Mac OS X after installing geckodriver or chromedriver):
    ./run_tests.sh -selenium test/selenium_tests/test_registration.py:RegistrationTestCase.test_reregister_username_fails

Note About Selenium Tests:

If using a local selenium driver such as a Chrome or Firefox based one
either chromedriver or geckodriver needs to be installed an placed on
the PATH.

More information on geckodriver can be found at
https://github.com/mozilla/geckodriver and more information on
chromedriver can be found at
https://sites.google.com/a/chromium.org/chromedriver/.

By default Galaxy will check the PATH for these and pick
whichever it finds. This can be overridden by setting
GALAXY_TEST_SELENIUM_BROWSER to either FIREFOX, CHROME, or something
more esoteric (including OPERA and PHANTOMJS).

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
 --debug               On python test error or failure invoke a pdb shell for
                       interactive debugging of the test
 --report_file         Path of HTML report to produce (for Python Galaxy
                       functional tests). If not given, a default filename will
                       be used, and reported on stderr at the end of the run.
 --xunit_report_file   Path of XUnit report to produce (for Python Galaxy
                       functional tests).
 --skip-venv           Do not create .venv (passes this flag to
                       common_startup.sh)
 --dockerize           Run tests in a pre-configured Docker container (must be
                       first argument if present).
 --db <type>           For use with --dockerize, run tests using partially
                       migrated 'postgres', 'mysql', or 'sqlite' databases.
 --external_url        External URL to use for Galaxy testing (only certain
                       tests).
 --external_master_key Master API key used to configure external tests.
 --external_user_key   User API used for external tests - not required if
                       external_master_key is specified.

Environment Variables:

In addition to the above command-line options, many environment variables
can be used to control the Galaxy functional testing processing. Command-line
options above like (--external_url) will set environment variables - in such
cases the command line argument takes precedent over environment variables set
at the time of running this script.

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
GALAXY_CONFIG_MASTER_KEY        Master or admin API key to use as part of
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
TOOL_SHED_TEST_HOST             Host to use for shed server setup for testing.
TOOL_SHED_TEST_PORT             Port to use for shed server setup for testing.
TOOL_SHED_TEST_FILE_DIR         Defaults to test/shed_functional/test_data.
TOOL_SHED_TEST_TMP_DIR          Defaults to random /tmp directory - place for
                                tool shed test server files to be placed.
TOOL_SHED_TEST_OMIT_GALAXY      Do not launch a Galaxy server for tool shed
                                testing.

Unit Test Environment Variables

GALAXY_TEST_INCLUDE_SLOW - Used in unit tests to trigger slower tests that
                           aren't included by default with --unit/-u.

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

ensure_grunt_for_qunit() {
    if ! exists "grunt";
    then
        PATH="$PATH:./test/qunit/node_modules/grunt/bin"
        export PATH
        if ! exists "grunt";
        then
            echo "Grunt not on path, cannot run these tests."
            exit 1
        fi
    fi
}


DOCKER_DEFAULT_IMAGE='galaxy/testing-base:17.05.0'

test_script="./scripts/functional_tests.py"
report_file="run_functional_tests.html"
xunit_report_file=""
structured_data_report_file=""
with_framework_test_tools_arg=""

driver="python"

if [ "$1" = "--dockerize" ];
then
    shift
    DOCKER_EXTRA_ARGS=${DOCKER_ARGS:-""}
    DOCKER_RUN_EXTRA_ARGS=${DOCKER_RUN_EXTRA_ARGS:-""}
    DOCKER_IMAGE=${DOCKER_IMAGE:-${DOCKER_DEFAULT_IMAGE}}
    if [ "$1" = "--db" ]; then
       db_type=$2
       shift 2
    else
       db_type="sqlite"
    fi
    if [ "$1" = "--external_tmp" ]; then
       # If /tmp is a tmpfs there may be better performance by reusing
       # the parent's temp file system. Also, it seems to decrease the
       # frequency or errors such as the following:
       # /bin/sh: 1: /tmp/tmpiWU3kJ/tmp_8zLxx/job_working_directory_mwwDmg/000/274/galaxy_274.sh: Text file busy
       tmp=$(mktemp -d)
       chmod 1777 $tmp
       DOCKER_RUN_EXTRA_ARGS="-v ${tmp}:/tmp ${DOCKER_RUN_EXTRA_ARGS}"
       shift
    fi
    MY_UID=$(id -u)
    DOCKER_RUN_EXTRA_ARGS="-e GALAXY_TEST_UID=${MY_UID} ${DOCKER_RUN_EXTRA_ARGS}"
    echo "Launching docker container for testing..."
    docker $DOCKER_EXTRA_ARGS run $DOCKER_RUN_EXTRA_ARGS -e "BUILD_NUMBER=$BUILD_NUMBER" -e "GALAXY_TEST_DATABASE_TYPE=$db_type" --rm -v `pwd`:/galaxy $DOCKER_IMAGE "$@"
    exit $?
fi

# If in Jenkins environment, create xunit-${BUILD_NUMBER}.xml by default.
if [ -n "$BUILD_NUMBER" ];
then
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
      -l|-list|--list)
          show_list
          exit 0
          ;;
      -id|--id)
          if [ $# -gt 1 ]; then
              test_id=$2;
              shift 2
          else
              echo "--id requires an argument" 1>&2
              exit 1
          fi
          ;;
      -s|-sid|--sid)
          if [ $# -gt 1 ]; then
              section_id=$2
              shift 2
          else
              echo "--sid requires an argument" 1>&2
              exit 1
          fi
          ;;
      -a|-api|--api)
          with_framework_test_tools_arg="-with_framework_test_tools"
          test_script="./scripts/functional_tests.py"
          report_file="./run_api_tests.html"
          if [ $# -gt 1 ]; then
        	  api_script=$2
              shift 2
          else
              api_script="./test/api"
              shift 1
          fi
          ;;
      -selenium|--selenium)
          with_framework_test_tools_arg="-with_framework_test_tools"
          test_script="./scripts/functional_tests.py"
          report_file="./run_selenium_tests.html"
          selenium_test=1;
          if [ $# -gt 1 ]; then
              selenium_script=$2
              shift 2
          else
              selenium_script="./test/selenium_tests"
              shift 1
          fi
          ;;
      -t|-toolshed|--toolshed)
          test_script="./test/shed_functional/functional_tests.py"
          report_file="run_toolshed_tests.html"
          if [ $# -gt 1 ]; then
              toolshed_script=$2
              shift 2
          else
              toolshed_script="./test/shed_functional/functional"
              shift 1
          fi
          ;;
      -clean_pyc|--clean_pyc)
          find lib -iname '*pyc' -exec rm -rf {} \;
          find test -iname '*pyc' -exec rm -rf {} \;
          shift
          ;;
      -with_framework_test_tools|--with_framework_test_tools)
          with_framework_test_tools_arg="-with_framework_test_tools"
          shift
          ;;
      --external_url)
          GALAXY_TEST_EXTERNAL=$2
          shift 2
          ;;
      --external_master_key)
          GALAXY_CONFIG_MASTER_KEY=$2
          shift 2
          ;;
      --external_user_key)
          GALAXY_TEST_USER_API_KEY=$2
          shift 2
          ;;
      -f|-framework|--framework)
          report_file="run_framework_tests.html"
          framework_test=1;
          shift 1
          ;;
      -d|-data_managers|--data_managers)
          data_managers_test=1;
          shift 1
          ;;
      -j|-casperjs|--casperjs)
          # TODO: Support running casper tests against existing
          # Galaxy instances.
          with_framework_test_tools_arg="-with_framework_test_tools"
          if [ $# -gt 1 ]; then
              casperjs_test_name=$2
              shift 2
          else
              shift 1
          fi
          report_file="run_casperjs_tests.html"
          casperjs_test=1;
          ;;
      -m|-migrated|--migrated)
          migrated_test=1;
          shift
          ;;
      -i|-installed|--installed)
          installed_test=1;
          shift
          ;;
      -r|--report_file)
          if [ $# -gt 1 ]; then
              report_file=$2
              shift 2
          else
              echo "--report_file requires an argument" 1>&2
              exit 1
          fi
          ;;
      --xunit_report_file)
          if [ $# -gt 1 ]; then
              xunit_report_file=$2
              shift 2
          else
              echo "--xunit_report_file requires an argument" 1>&2
              exit 1
          fi
          ;;
      --structured_data_report_file)
          if [ $# -gt 1 ]; then
              structured_data_report_file=$2
              shift 2
          else
              echo "--structured_data_report_file requires an argument" 1>&2
              exit 1
          fi
          ;;
      --verbose_errors)
          GALAXY_TEST_VERBOSE_ERRORS=True
          export GALAXY_TEST_VERBOSE_ERRORS
          shift
          ;;
      -c|--coverage)
          # Must have coverage installed (try `which coverage`) - only valid with --unit
          # for now. Would be great to get this to work with functional tests though.
          coverage_arg="--with-coverage"
          NOSE_WITH_COVERAGE=true
          shift
          ;;
      --debug)
          #TODO ipdb would be nicer.
          NOSE_PDB=True
          export NOSE_PDB
          shift
          ;;
      -u|-unit|--unit)
          report_file="run_unit_tests.html"
          test_script="./scripts/nosetests.py"
          if [ $# -gt 1 ]; then
              unit_extra=$2
              shift 2
          else
              unit_extra='--exclude=functional --exclude="^get" --exclude=controllers --exclude=runners --exclude dictobj --exclude=jstree lib test/unit'
              shift 1
          fi
          ;;
      -i|-integration|--integration)
          report_file="run_integration_tests.html"
          test_script="./scripts/nosetests.py"
          if [ $# -gt 1 ]; then
              integration_extra=$2
              shift 2
          else
              integration_extra='test/integration'
              shift 1
          fi
          ;;
      -q|-qunit|--qunit)
          # Requires grunt installed and dependencies configured see
          # test/qunit/README.txt for more information.
          driver="grunt"
          gruntfile="./test/qunit/Gruntfile.js"
          if [ $# -gt 1 ]; then
              qunit_name=$2
              shift 2
          else
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
      -watch|--watch)
          # Have grunt watch test or directory for changes, only
          # valid for javascript testing.
          watch=1
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
      --no-replace-pip)
          no_replace_pip='--no-replace-pip'
          shift
          ;;
      --replace-pip)
          replace_pip='--replace-pip'
          shift
          ;;
      --skip-common-startup)
          # Don't run ./scripts/common_startup.sh (presumably it has already
          # been done, or you know what you're doing).
          skip_common_startup=1
          shift
          ;;
      --)
          shift
          break
          ;;
      -*)
          echo "invalid option: $1" 1>&2;
          show_help
          exit 1
          ;;
      *)
          break;
          ;;
    esac
done

if [ -z "$skip_common_startup" ]; then
    if [ -n "$GALAXY_TEST_DBURI" ]; then
            GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION=$GALAXY_TEST_DBURI
            export GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION
    fi
    ./scripts/common_startup.sh $skip_venv $no_create_venv $no_replace_pip $replace_pip --dev-wheels || exit 1
fi

GALAXY_VIRTUAL_ENV="${GALAXY_VIRTUAL_ENV:-.venv}"
if [ -z "$skip_venv" -a -d "$GALAXY_VIRTUAL_ENV" ];
then
    printf "Activating virtualenv at $GALAXY_VIRTUAL_ENV\n"
    . "$GALAXY_VIRTUAL_ENV/bin/activate"
fi

if [ -n "$migrated_test" ] ; then
    [ -n "$test_id" ] && class=":TestForTool_$test_id" || class=""
    extra_args="functional.test_toolbox$class -migrated"
elif [ -n "$installed_test" ] ; then
    [ -n "$test_id" ] && class=":TestForTool_$test_id" || class=""
    extra_args="functional.test_toolbox$class -installed"
elif [ -n "$framework_test" ] ; then
    [ -n "$test_id" ] && class=":TestForTool_$test_id" || class=""
    extra_args="functional.test_toolbox$class -framework"
elif [ -n "$selenium_test" ] ; then
    extra_args="$selenium_script -selenium"
elif [ -n "$data_managers_test" ] ; then
    [ -n "$test_id" ] && class=":TestForDataManagerTool_$test_id" || class=""
    extra_args="functional.test_data_managers$class -data_managers"
elif [ -n "$toolshed_script" ]; then
    extra_args="$toolshed_script"
elif [ -n "$api_script" ]; then
    extra_args="$api_script"
elif [ -n "$casperjs_test" ]; then
    # TODO: Ensure specific versions of casperjs and phantomjs are
    # available. Some option for leveraging npm to automatically
    # install these dependencies would be nice as well.
    if [ -n "$casperjs_test_name" ]; then
        extra_args="test/casperjs/casperjs_runner.py:$casperjs_test_name"
    else
        extra_args="test/casperjs/casperjs_runner.py"
    fi
elif [ -n "$section_id" ]; then
    extra_args=`python tool_list.py $section_id`
elif [ -n "$test_id" ]; then
    class=":TestForTool_$test_id"
    extra_args="functional.test_toolbox$class"
elif [ -n "$unit_extra" ]; then
    extra_args="--with-doctest $unit_extra"
elif [ -n "$integration_extra" ]; then
    extra_args="$integration_extra"
elif [ -n "$1" ] ; then
    extra_args="$1"
else
    extra_args='--exclude="^get" functional'
fi

if [ "$driver" = "python" ]; then
    if [ -n "$xunit_report_file" ]; then
        xunit_args="--with-xunit --xunit-file $xunit_report_file"
    else
        xunit_args=""
    fi
    if [ -n "$structured_data_report_file" ]; then
        structured_data_args="--with-structureddata --structured-data-file $structured_data_report_file"
    else
        structured_data_args=""
    fi
    if [ -n "$with_framework_test_tools_arg" ]; then
        GALAXY_TEST_TOOL_CONF="config/tool_conf.xml.sample,test/functional/tools/samples_tool_conf.xml"
        export GALAXY_TEST_TOOL_CONF
    fi
    python $test_script $coverage_arg -v --with-nosehtml --html-report-file $report_file $xunit_args $structured_data_args $extra_args
    exit_status=$?
    echo "Testing complete. HTML report is in \"$report_file\"." 1>&2
    exit ${exit_status}
else
    ensure_grunt_for_qunit
    if [ -n "$watch" ]; then
        grunt_task="watch"
    else
        grunt_task=""
    fi
    if [ -n "$qunit_name" ]; then
        grunt_args="--test=$qunit_name"
    else
        grunt_args=""
    fi
    # TODO: Exapnd javascript helpers to include setting up
    # grunt deps in npm, "watch"ing directory, and running casper
    # functional tests.
    grunt --gruntfile=$gruntfile $grunt_task $grunt_args
fi
