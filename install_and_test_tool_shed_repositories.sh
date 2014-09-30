#!/bin/sh

# A good place to look for nose info: http://somethingaboutorange.com/mrl/projects/nose/

# The test/install_and_test_tool_shed_repositories/functional_tests.py cannot be executed directly because it must
# have certain functional test definitions in sys.argv.  Running it through this shell script is the best way to
# ensure that it has the required definitions.

# This script requires setting of the following environment variables:
# GALAXY_INSTALL_TEST_TOOL_SHED_API_KEY - must be set to the API key for the tool shed that is being checked.
# GALAXY_INSTALL_TEST_TOOL_SHED_URL - must be set to a URL that the tool shed is listening on.

# If the tool shed url is not specified in tool_sheds_conf.xml, GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF must be set to
# a tool sheds configuration file that does specify that url or repository installation will fail.

# This script accepts the command line option -w to select which set of tests to run. The default behavior is to test
# first tool_dependency_definition repositories and then repositories with tools. Provide the value 'dependencies'
# to test only tool_dependency_definition repositories or 'tools' to test only repositories with tools. 

if [ -z $GALAXY_INSTALL_TEST_TOOL_SHED_API_KEY ] ; then
	echo "This script requires the GALAXY_INSTALL_TEST_TOOL_SHED_API_KEY environment variable to be set and non-empty."
	exit 1
fi

if [ -z $GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR ] ; then
	echo "This script requires the GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR environment variable to be set to your configured tool dependency path."
	exit 1
fi

if [ -z $GALAXY_INSTALL_TEST_TOOL_SHED_URL ] ; then
	echo "This script requires the GALAXY_INSTALL_TEST_TOOL_SHED_URL environment variable to be set and non-empty."
	exit 1
fi

if [ -z "$GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF" ] ; then
	if grep --quiet $GALAXY_INSTALL_TEST_TOOL_SHED_URL config/tool_sheds_conf.xml.sample; then
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

if [ -z $GALAXY_INSTALL_TEST_SHED_TOOL_PATH ] ; then
	export GALAXY_INSTALL_TEST_SHED_TOOL_PATH='/tmp/shed_tools'
fi

if [ ! -d $GALAXY_INSTALL_TEST_SHED_TOOL_PATH ] ; then
	mkdir -p $GALAXY_INSTALL_TEST_SHED_TOOL_PATH
fi

if [ ! -d $GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR ] ; then
    mkdir -p $GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR
fi

test_tool_dependency_definitions () {
    # Test installation of repositories of type tool_dependency_definition.
	if [ -f $GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR/stage_1_complete ] ; then
		rm $GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR/stage_1_complete
	fi
    echo "Starting stage 1, tool dependency definitions."
    python test/install_and_test_tool_shed_repositories/tool_dependency_definitions/functional_tests.py $* -v --with-nosehtml --html-report-file \
        test/install_and_test_tool_shed_repositories/tool_dependency_definitions/run_functional_tests.html \
        test/install_and_test_tool_shed_repositories/functional/test_install_repositories.py \
        test/functional/test_toolbox.py
    echo "Stage 1 complete, exit code $?"
    touch $GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR/stage_1_complete
}

test_repositories_with_tools () {
	if [ ! -f $GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR/stage_1_complete ] ; then
		echo 'Stage 1 did not complete its run, exiting.'
		exit 1
	fi
    echo "Starting stage 2, repositories with tools."
    # Test installation of repositories that contain valid tools with defined functional tests and a test-data directory containing test files.
    python test/install_and_test_tool_shed_repositories/repositories_with_tools/functional_tests.py $* -v --with-nosehtml --html-report-file \
        test/install_and_test_tool_shed_repositories/repositories_with_tools/run_functional_tests.html \
        test/install_and_test_tool_shed_repositories/functional/test_install_repositories.py \
        test/functional/test_toolbox.py
    echo "Stage 2 complete, exit code $?"
    rm $GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR/stage_1_complete
}

which='both'

while getopts "w:" arg; do
    case $arg in
        w)
            which=$OPTARG
            ;;
    esac
done

case $which in
    # Use "-w tool_dependency_definitions" when you want to test repositories of type tool_dependency_definition.
    tool_dependency_definitions)
        test_tool_dependency_definitions
        ;;
    # Use "-w repositories_with_tools" parameter when you want to test repositories that contain tools.
    repositories_with_tools)
        touch $GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR/stage_1_complete
        test_repositories_with_tools
        ;;
    # No received parameters or any received parameter not in [ tool_dependency_definitions, repositories_with_tools ]
    # will execute both scripts.
    *)
        test_tool_dependency_definitions
        test_repositories_with_tools
        ;;
esac        
