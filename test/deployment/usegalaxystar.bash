#!/bin/bash

# Once-a-release deployment tests for usegalaxy*
# This script is designed for use with .github/workflows/deployment.yaml,
# a manually triggered GitHub Actions workflow.
# The variables this script consumes include:
# - GALAXY_TEST_DEPLOYMENT_TARGET
#    target Galaxy deployment to test against - this should be
#    usegalaxymain or usegalaxytest currently.
# - GALAXY_TEST_DEPLOYMENT_DEBUG
#    should be the string "true" to enable additional debugging
# - GALAXY_TEST_USEGALAXYMAIN_USER_KEY
#   GALAXY_TEST_USEGALAXYTEST_USER_KEY
#    API key to select for given target.

set -e

echo "Deployment target is $GALAXY_TEST_DEPLOYMENT_TARGET"

# Setup dependencies and activate resulting Python environment.
./scripts/common_startup.sh --skip-client-build --skip-node
. .venv/bin/activate

if [ $GALAXY_TEST_DEPLOYMENT_DEBUG = "true" ];
then
    PYTEST_DEBUG_ARGS="-s -v"
else
    PYTEST_DEBUG_ARGS=""
fi

if [ "$GALAXY_TEST_DEPLOYMENT_TARGET" = "usegalaxymain" ];
then
    GALAXY_TEST_EXTERNAL="https://usegalaxy.org"
    GALAXY_TEST_USER_API_KEY="$GALAXY_TEST_USEGALAXYMAIN_USER_KEY"
    GALAXY_TEST_USER_EMAIL="$GALAXY_TEST_USEGALAXYMAIN_USER_EMAIL"
    GALAXY_TEST_SELENIUM_USER_PASSWORD="$GALAXY_TEST_USEGALAXYMAIN_USER_PASSWORD"
elif [ "$GALAXY_TEST_DEPLOYMENT_TARGET" = "usegalaxytest" ];
then
    GALAXY_TEST_EXTERNAL="https://test.galaxyproject.org"
    GALAXY_TEST_USER_API_KEY="$GALAXY_TEST_USEGALAXYTEST_USER_KEY"
    GALAXY_TEST_USER_EMAIL="$GALAXY_TEST_USEGALAXYTEST_USER_EMAIL"
    GALAXY_TEST_SELENIUM_USER_PASSWORD="$GALAXY_TEST_USEGALAXYTEST_USER_PASSWORD"
elif [ "$GALAXY_TEST_DEPLOYMENT_TARGET" = "usegalaxyeu" ];
then
    GALAXY_TEST_EXTERNAL="https://usegalaxy.eu"
    GALAXY_TEST_USER_API_KEY="$GALAXY_TEST_USEGALAXYEU_USER_KEY"
    GALAXY_TEST_USER_EMAIL="$GALAXY_TEST_USEGALAXYEU_USER_EMAIL"
    GALAXY_TEST_SELENIUM_USER_PASSWORD="$GALAXY_TEST_USEGALAXYEU_USER_PASSWORD"
else
    echo "ERROR: Unknown deployment test target ${GALAXY_TEST_DEPLOYMENT_TARGET}"
    exit 1
fi
export GALAXY_TEST_EXTERNAL
export GALAXY_TEST_USER_API_KEY
export GALAXY_TEST_USER_EMAIL
GALAXY_TEST_SELENIUM_USER_EMAIL="$GALAXY_TEST_USER_EMAIL"
export GALAXY_TEST_SELENIUM_USER_EMAIL
export GALAXY_TEST_SELENIUM_USER_PASSWORD

api_tests=(
    lib/galaxy_test/api/test_datatypes.py
    lib/galaxy_test/api/test_workflow_extraction.py
    lib/galaxy_test/api/test_users.py
    lib/galaxy_test/api/test_roles.py
    lib/galaxy_test/api/test_authenticate.py
    lib/galaxy_test/api/test_configuration.py
    lib/galaxy_test/api/test_dataset_collections.py
    lib/galaxy_test/api/test_display_applications.py
    lib/galaxy_test/api/test_drs.py
    lib/galaxy_test/api/test_folders.py
    lib/galaxy_test/api/test_folder_contents.py
    lib/galaxy_test/api/test_framework.py
    lib/galaxy_test/api/test_histories.py
    lib/galaxy_test/api/test_history_contents.py
)
selenium_tests=(
    lib/galaxy_test/selenium/test_anon_history.py
    lib/galaxy_test/selenium/test_collection_builders.py
    lib/galaxy_test/selenium/test_dataset_metadata_download.py
    lib/galaxy_test/selenium/test_collection_edit.py
    lib/galaxy_test/selenium/test_history_copy_elements.py
    lib/galaxy_test/selenium/test_history_dataset_state.py
    lib/galaxy_test/selenium/test_history_multi_view.py
)
if [ "$GALAXY_TEST_DEPLOYMENT_TEST_TYPE" = "all" ];
then
    tests=("${api_tests[@]}" "${selenium_tests[@]}")
elif [ "$GALAXY_TEST_DEPLOYMENT_TEST_TYPE" = "api" ];
then
    tests=("${api_tests[@]}")
elif [ "$GALAXY_TEST_DEPLOYMENT_TEST_TYPE" = "selenium" ];
then
    tests=("${selenium_tests[@]}")
else
    echo "Unknown GALAXY_TEST_DEPLOYMENT_TEST_TYPE encountered ${GALAXY_TEST_DEPLOYMENT_TEST_TYPE}"
    exit 1
fi

echo "Running tests: ${tests[@]}"
# pytest markers to select against. In order to not cause an explosion of
# semi-permanent artifacts that are difficult to manage tests which require
# new libraries or users are disabled. Tests which require admin keys are
# also disabled for security/simplicity reasons.
PYTEST_MARKER_EXPRESSION="not requires_admin and not requires_new_library and not requires_new_user and not requires_celery"
PYTEST_HTML_REPORT="deployment_tests.html"
pytest \
    $PYTEST_DEBUG_ARGS \
    --html "$PYTEST_HTML_REPORT" \
    -m "${PYTEST_MARKER_EXPRESSION}" \
    "${tests[@]}"
