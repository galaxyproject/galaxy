#!/bin/sh

# A good place to look for nose info: http://somethingaboutorange.com/mrl/projects/nose/

# The test/install_and_test_tool_shed_repositories/functional_tests.py can not be executed directly, because it must have certain functional test definitions
# in sys.argv. Running it through this shell script is the best way to ensure that it has the required definitions.

# This script requires the following environment variables:
# GALAXY_INSTALL_TEST_TOOL_SHED_API_KEY - must be set to the API key for the tool shed that is being checked.
# GALAXY_INSTALL_TEST_TOOL_SHED_URL - must be set to a URL that the tool shed is listening on.
# If the tool shed url is not specified in tool_sheds_conf.xml, GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF must be set to a tool sheds configuration file
# that does specify that url, otherwise repository installation will fail.

if [ -z $GALAXY_INSTALL_TEST_TOOL_SHED_API_KEY ] ; then
	echo "This script requires the GALAXY_INSTALL_TEST_TOOL_SHED_API_KEY environment variable to be set and non-empty."
	exit 1
fi

if [ -z $GALAXY_INSTALL_TEST_TOOL_SHED_URL ] ; then
	echo "This script requires the GALAXY_INSTALL_TEST_TOOL_SHED_URL environment variable to be set and non-empty."
	exit 1
fi

if [ -z "$GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF" ] ; then
	if grep --quiet $GALAXY_INSTALL_TEST_TOOL_SHED_URL tool_sheds_conf.xml; then
		echo "Tool sheds configuration tool_sheds_conf.xml ok, proceeding."
	else
		echo "ERROR: Tool sheds configuration tool_sheds_conf.xml does not have an entry for $GALAXY_INSTALL_TEST_TOOL_SHED_URL."
		exit 1
	fi
else
	if grep --quiet $GALAXY_INSTALL_TEST_TOOL_SHED_URL $GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF; then
		echo "Tool sheds configuration $GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF ok, proceeding."
	else
		echo "ERROR: Tool sheds configuration $GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF does not have an entry for $GALAXY_INSTALL_TEST_TOOL_SHED_URL"
		exit 1
	fi
fi

python test/install_and_test_tool_shed_repositories/functional_tests.py $* -v --with-nosehtml --html-report-file \
	test/install_and_test_tool_shed_repositories/run_functional_tests.html \
	test/install_and_test_tool_shed_repositories/functional/test_install_repositories.py \
	test/functional/test_toolbox.py  
