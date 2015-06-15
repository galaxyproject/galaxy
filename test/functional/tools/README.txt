This directory contains tools only useful for testing and
demonstrating aspects of the tool syntax. Run the test driver script
'run_tests.sh' with the '-framework' as first argument to run through
these tests. Pass in an '-id' along with one of these tool ids to test
a single tool.

Finally, to play around with these tools interactively - simply
replace the 'galaxy.ini' option 'tool_config_file' with:

tool_config_file = test/functional/tools/samples_tool_conf.xml
