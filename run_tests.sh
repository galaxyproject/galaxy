#!/bin/sh

# A good place to look for nose info: http://somethingaboutorange.com/mrl/projects/nose/
rm -f run_functional_tests.log 

show_help() {
cat <<EOF
'${0##*/}'                          for testing all the tools in functional directory
'${0##*/} aaa'                      for testing one test case of 'aaa' ('aaa' is the file name with path)
'${0##*/} -id bbb'                  for testing one tool with id 'bbb' ('bbb' is the tool id)
'${0##*/} -sid ccc'                 for testing one section with sid 'ccc' ('ccc' is the string after 'section::')
'${0##*/} -list'                    for listing all the tool ids
'${0##*/} -api'                     for running all the test scripts in the ./test/api directory
'${0##*/} -toolshed'                for running all the test scripts in the ./test/tool_shed/functional directory
'${0##*/} -toolshed testscriptname' for running one test script named testscriptname in the .test/tool_shed/functional directory
'${0##*/} -workflow test.xml'       for running a workflow test case as defined by supplied workflow xml test file (experimental)
'${0##*/} -framework'               for running through example tool tests testing framework features in test/functional/tools"   
'${0##*/} -framework -id toolid'    for testing one framework tool (in test/functional/tools/) with id 'toolid'
'${0##*/} -data_managers -id data_manager_id'    for testing one Data Manager with id 'data_manager_id'
'${0##*/} -unit'                    for running all unit tests (doctests in lib and tests in test/unit)
'${0##*/} -unit testscriptath'      running particular tests scripts
'${0##*/} -qunit'                   for running qunit JavaScript tests
'${0##*/} -qunit testname'          for running single JavaScript test with given name
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


test_script="./scripts/functional_tests.py"
report_file="run_functional_tests.html"
with_framework_test_tools_arg=""

driver="python"

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
          report_file="./test/tool_shed/run_functional_tests.html"
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
          casperjs_test=1;
          shift
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
      -c|--coverage)
          # Must have coverage installed (try `which coverage`) - only valid with --unit
          # for now. Would be great to get this to work with functional tests though.
          coverage_arg="--with-coverage"
          NOSE_WITH_COVERAGE=true
          shift
          ;;
      -u|-unit|--unit)
          report_file="run_unit_tests.html"
          test_script="./scripts/nosetests.py"
          if [ $# -gt 1 ]; then
              unit_extra=$2
              shift 2
          else 
              unit_extra='--exclude=functional --exclude="^get" --exclude=controllers --exclude=runners lib test/unit'
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
      -watch|--watch)
          # Have grunt watch test or directory for changes, only
          # valid for javascript testing.
          watch=1
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
    extra_args="test/casperjs/casperjs_runner.py"
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
    python $test_script $coverage_arg -v --with-nosehtml --html-report-file $report_file $with_framework_test_tools_arg $extra_args
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
