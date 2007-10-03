#!/bin/sh

# A good place to look for nose info: http://somethingaboutorange.com/mrl/projects/nose/

rm -f run_functional_tests.log 
echo "'run_functional_tests.sh help'                  for help"

if [ ! $1 ]; then
	./nosetests.sh -v -w test --with-nosehtml --html-report-file run_functional_tests.html --exclude="^get" functional
elif [ $1 = 'help' ]; then
	echo "'run_functional_tests.sh'                       for testing all the tools in functional directory"
	echo "'run_functional_tests.sh aaa'                   for testing one test case, 'aaa'"
	echo "'run_functional_tests.sh -id bbb'               for testing one tool with id 'bbb'"
	echo "'run_functional_tests.sh -list'                 for listing all the tool ids"
elif [ $1 = '-id' ]; then
	./nosetests.sh -v -w test functional.test_toolbox:GeneratedToolTestCase_$2 --with-nosehtml --html-report-file run_functional_tests.html
elif [ $1 = '-list' ]; then
    python tool_list.py
	echo "==========================================================================================================================================="
    echo "'run_functional_tests.sh help'                  for help"
	echo "'run_functional_tests.sh -id bbb'               for testing one tool with id 'bbb'"
else
	./nosetests.sh -v -w test --with-nosehtml --html-report-file run_functional_tests.html $1
fi

