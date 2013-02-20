#!/bin/sh

# A good place to look for nose info: http://somethingaboutorange.com/mrl/projects/nose/
#rm -f ./test/tool_shed/run_functional_tests.log 

python test/install_and_test_tool_shed_repositories/functional_tests.py -v --with-nosehtml --html-report-file ./test/install_and_test_tool_shed_repositories/run_functional_tests.html test/install_and_test_tool_shed_repositories/functional/test_install_repositories.py test/functional/test_toolbox.py 

