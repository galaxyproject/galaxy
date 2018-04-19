#!/bin/bash

# Enable retries on tests to reduce chances of transient failures.
: ${GALAXY_TEST_SELENIUM_RETRIES:=1}
: ${GALAXY_TEST_CLIENT_BUILD_IMAGE:='node:9.4.0'}

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

# /etc/passwd hack needed as long as make client requires git.
# https://github.com/galaxyproject/galaxy/issues/5912
docker run -v /etc/passwd:/etc/passwd -v `pwd`:`pwd`:rw -w `pwd` -u $UID $GALAXY_TEST_CLIENT_BUILD_IMAGE /bin/bash -c 'make client-production-maps'

# Start Selenium server in the test Docker container.
DOCKER_RUN_EXTRA_ARGS="-e USE_SELENIUM=1 -e GALAXY_TEST_SELENIUM_RETRIES=${GALAXY_TEST_SELENIUM_RETRIES} -e GALAXY_TEST_ERRORS_DIRECTORY=${GALAXY_TEST_ERRORS_DIRECTORY} -e GALAXY_TEST_SCREENSHOTS_DIRECTORY=${GALAXY_TEST_SCREENSHOTS_DIRECTORY} ${DOCKER_RUN_EXTRA_ARGS}"
export DOCKER_RUN_EXTRA_ARGS

./run_tests.sh --dockerize --db postgres --external_tmp --clean_pyc --skip_flakey_fails --selenium "$@"
