#!/bin/bash

# Enable retries on tests to reduce chances of transient failures.
: ${GALAXY_TEST_SELENIUM_RETRIES:=1}

# If in Jenkins environment, use it for artifacts.
if [ -n "$BUILD_NUMBER" ];
then
    : ${GALAXY_TEST_ERRORS_DIRECTORY:=${BUILD_NUMBER}-test-errors}
    : ${GALAXY_TEST_SCREENSHOTS_DIRECTORY:=${BUILD_NUMBER}-test-screenshots}
else
    : ${GALAXY_TEST_ERRORS_DIRECTORY:=database/test-errors}
    : ${GALAXY_TEST_SCREENSHOTS_DIRECTORY:=database/test-screenshots}
fi

mkdir -p "$GALAXY_TEST_ERRORS_DIRECTORY"
mkdir -p "$GALAXY_TEST_SCREENSHOTS_DIRECTORY"

mkdir -p ~/.jenkins-yarn-cache
YARN_CACHE_FOLDER=~/.jenkins-yarn-cache

# Start Selenium server in the test Docker container.
DOCKER_RUN_EXTRA_ARGS="${DOCKER_RUN_EXTRA_ARGS} --shm-size=2g -v $YARN_CACHE_FOLDER:$YARN_CACHE_FOLDER -e YARN_CACHE_FOLDER=$YARN_CACHE_FOLDER -e USE_SELENIUM=1 -e GALAXY_TEST_SELENIUM_RETRIES=${GALAXY_TEST_SELENIUM_RETRIES} -e GALAXY_TEST_ERRORS_DIRECTORY=${GALAXY_TEST_ERRORS_DIRECTORY} -e GALAXY_TEST_SCREENSHOTS_DIRECTORY=${GALAXY_TEST_SCREENSHOTS_DIRECTORY}"
export DOCKER_RUN_EXTRA_ARGS

./run_tests.sh --dockerize --python3 --db postgres --clean_pyc --skip_flakey_fails --selenium "$@"
