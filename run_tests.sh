#!/bin/sh

pwd_dir=$(pwd)
cd `dirname $0`

# A good place to look for nose info: http://somethingaboutorange.com/mrl/projects/nose/
rm -f run_functional_tests.log

show_help() {
cat <<EOF
'${0##*/} (test_path)'              for testing all the tools in functional directory
'${0##*/} -id bbb'                  for testing one tool with id 'bbb' ('bbb' is the tool id)
'${0##*/} -sid ccc'                 for testing one section with sid 'ccc' ('ccc' is the string after 'section::')
'${0##*/} -list'                    for listing all the tool ids
'${0##*/} -api (test_path)'         for running all the test scripts in the ./test/api directory
'${0##*/} -toolshed (test_path)'    for running all the test scripts in the ./test/tool_shed/functional directory
'${0##*/} -workflow test.xml'       for running a workflow test case as defined by supplied workflow xml test file (experimental)
'${0##*/} -installed'               for running tests of Tool Shed installed tools
'${0##*/} -framework'               for running through example tool tests testing framework features in test/functional/tools"
'${0##*/} -framework -id toolid'    for testing one framework tool (in test/functional/tools/) with id 'toolid'
'${0##*/} -data_managers -id data_manager_id'    for testing one Data Manager with id 'data_manager_id'
'${0##*/} -unit (test_path)'        for running all unit tests (doctests in lib and tests in test/unit)
'${0##*/} -qunit'                   for running qunit JavaScript tests
'${0##*/} -qunit testname'          for running single JavaScript test with given name
'${0##*/} -casperjs (py_test_path)' for running casperjs JavaScript tests using a Python wrapper for consistency. py_test_path in casperjs_runner.py e.g. 'Test_04_HDAs' or 'Test_04_HDAs.test_00_HDA_states'.

Nose tests will allow specific tests to be selected per the documentation at
https://nose.readthedocs.org/en/latest/usage.html#selecting-tests.  These are
indicated with the optional parameter (test_path).  A few examples are:

Run all TestUserInfo functional tests:
    ./run_tests.sh test/functional/test_user_info.py:TestUserInfo

Run a specific API test:
    ./run_tests.sh -api test/api/test_tools.py:ToolsTestCase.test_map_over_with_output_format_actions


Extra options:
 --verbose_errors      Force some tests produce more verbose error reporting.
 --no_cleanup          Do not delete temp files for Python functional tests (-toolshed, -framework, etc...)
 --debug               On python test error or failure invoke a pdb shell for interactive debugging of the test
 --report_file         Path of HTML report to produce (for Python Galaxy functional tests).
 --xunit_report_file   Path of XUnit report to produce (for Python Galaxy functional tests).
 --skip-venv           Do not create .venv (passes this flag to common_startup.sh)
 --dockerize           Run tests in a pre-configured Docker container (must be first argument if present).
 --db <type>           For use with --dockerize, run tests using partially migrated 'postgres', 'mysql',
                       or 'sqlite' databases.
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

ensure_grunt() {
    if ! exists "grunt";
    then
        echo "Grunt not on path, cannot run these tests."
        exit 1
    fi
}


DOCKER_DEFAULT_IMAGE='galaxy/testing-base:15.10.2'

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
    docker $DOCKER_EXTRA_ARGS run $DOCKER_RUN_EXTRA_ARGS -e "GALAXY_TEST_DATABASE_TYPE=$db_type" --rm -v `pwd`:/galaxy $DOCKER_IMAGE "$@"
    exit $?
fi

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
      -t|-toolshed|--toolshed)
          test_script="./test/tool_shed/functional_tests.py"
          report_file="run_toolshed_tests.html"
          if [ $# -gt 1 ]; then
              toolshed_script=$2
              shift 2
          else
              toolshed_script="./test/tool_shed/functional"
              shift 1
          fi
          ;;
      -with_framework_test_tools|--with_framework_test_tools)
          with_framework_test_tools_arg="-with_framework_test_tools"
          shift
          ;;
      -w|-workflow|--workflow)
          if [ $# -gt 1 ]; then
              workflow_file=$2
              workflow_test=1
              shift 2
          else
              echo "--workflow requires an argument" 1>&2
              exit 1
          fi
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
    ./scripts/common_startup.sh $skip_venv --dev-wheels || exit 1
fi

if [ -z "$skip_venv" -a -d .venv ];
then
    printf "Activating virtualenv at %s/.venv\n" $(pwd)
    . .venv/bin/activate
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
elif [ -n "$data_managers_test" ] ; then
    [ -n "$test_id" ] && class=":TestForDataManagerTool_$test_id" || class=""
    extra_args="functional.test_data_managers$class -data_managers"
elif [ -n "$workflow_test" ]; then
    extra_args="functional.workflow:WorkflowTestCase $workflow_file"
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
    python $test_script $coverage_arg -v --with-nosehtml --html-report-file $report_file $xunit_args $structured_data_args $with_framework_test_tools_arg $extra_args
else
    ensure_grunt
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

