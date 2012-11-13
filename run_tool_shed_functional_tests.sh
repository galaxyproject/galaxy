#!/bin/sh

# A good place to look for nose info: http://somethingaboutorange.com/mrl/projects/nose/
#rm -f ./test/tool_shed/run_functional_tests.log 

if [ ! $1 ]; then
    python ./test/tool_shed/functional_tests.py -v --with-nosehtml --html-report-file ./test/tool_shed/run_functional_tests.html ./test/tool_shed/functional
elif [ $1 = 'help' ]; then
    echo "'run_tool_shed_functional_tests.sh'                for running all the test scripts in the ./test/tool_shed/functional directory"
    echo "'run_tool_shed_functional_tests.sh testscriptname' for running one test script named testscriptname in the .test/tool_shed/functional directory"
else
    python ./test/tool_shed/functional_tests.py -v --with-nosehtml --html-report-file ./test/tool_shed/run_functional_tests.html $1
fi

echo "'sh run_tool_shed_functional_tests.sh help' for help"
