#!/bin/bash

# Enable retries on tests to reduce chances of transient failures.
: ${GALAXY_TEST_SELENIUM_RETRIES:=1}
: ${GALAXY_TEST_ERRORS_DIRECTORY:=database/test-errors}

# Start Selenium server in the test Docker container.
DOCKER_RUN_EXTRA_ARGS="-e USE_SELENIUM=1 -e GALAXY_TEST_SELENIUM_RETRIES=${GALAXY_TEST_SELENIUM_RETRIES} -e GALAXY_TEST_ERRORS_DIRECTORY=${GALAXY_TEST_ERRORS_DIRECTORY} ${DOCKER_RUN_EXTRA_ARGS}"
export DOCKER_RUN_EXTRA_ARGS

./run_tests.sh --dockerize --db postgres --external_tmp --clean_pyc --selenium "$@"
