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

mkdir -p ~/.jenkins-yarn-cache
YARN_CACHE_FOLDER=~/.jenkins-yarn-cache

# Set git environment variables to enable Git. https://github.com/galaxyproject/galaxy/issues/5912
# Setup volume and environment variable to cache this users yarn build.
docker run -e GIT_COMMITTER_NAME=Jenkins -e GIT_COMMITTER_EMAIL=jenkins@galaxyproject.org \
           -e YARN_CACHE_FOLDER=$YARN_CACHE_FOLDER -v $YARN_CACHE_FOLDER:$YARN_CACHE_FOLDER:rw \
           -v `pwd`:`pwd`:rw -w `pwd` -u $UID $GALAXY_TEST_CLIENT_BUILD_IMAGE \
           /bin/bash -c 'make client-production-maps'

# Start Selenium server in the test Docker container.
DOCKER_RUN_EXTRA_ARGS="-v $YARN_CACHE_FOLDER:$YARN_CACHE_FOLDER -e YARN_CACHE_FOLDER=$YARN_CACHE_FOLDER -e USE_SELENIUM=1 -e GALAXY_TEST_SELENIUM_RETRIES=${GALAXY_TEST_SELENIUM_RETRIES} -e GALAXY_TEST_ERRORS_DIRECTORY=${GALAXY_TEST_ERRORS_DIRECTORY} -e GALAXY_TEST_SCREENSHOTS_DIRECTORY=${GALAXY_TEST_SCREENSHOTS_DIRECTORY} ${DOCKER_RUN_EXTRA_ARGS}"
export DOCKER_RUN_EXTRA_ARGS

./run_tests.sh --dockerize --python3 --db postgres --clean_pyc --skip_flakey_fails --selenium "$@"
