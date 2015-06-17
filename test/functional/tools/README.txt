This directory contains tools only useful for testing and
demonstrating aspects of the tool syntax. Run the test driver script
'run_tests.sh' with the '-framework' as first argument to run through
these tests. Pass in an '-id' along with one of these tool ids to test
a single tool.

Some API tests use these tools to test various features of the API,
tool, and workflow subsystems. Pass the argument
'-with_framework_test_tools' to 'run_tests.sh' in addition to '-api'
to ensure these tools get loaded during the testing process.

Finally, to play around with these tools interactively - simply
replace the 'galaxy.ini' option 'tool_config_file' with:

tool_config_file = test/functional/tools/samples_tool_conf.xml
