#!/bin/bash

# Once-a-release deployment tests for usegalaxy*
# This script is designed for use with .github/workflows/deployment.yaml,
# a manually triggered GitHub Actions workflow.
# The variables this script consumes include:
# - GALAXY_TEST_DEPLOYMENT_TARGET
#    target Galaxy deployment to test against - this should be
#    usegalaxymain, usegalaxytest or usegalaxyeu currently.
# - GALAXY_TEST_DEPLOYMENT_DEBUG
#    should be the string "true" to enable additional debugging
# - GALAXY_TEST_USEGALAXYMAIN_USER_KEY
#   GALAXY_TEST_USEGALAXYTEST_USER_KEY
#   GALAXY_TEST_USEGALAXYEU_USER_KEY
#    API key to select for given target.

set -e

echo "Deployment target is $GALAXY_TEST_DEPLOYMENT_TARGET"

# Setup dependencies and activate resulting Python environment.
./scripts/common_startup.sh --skip-client-build --dev-wheels
. .venv/bin/activate

if [ "$GALAXY_TEST_DEPLOYMENT_DEBUG" = "true" ];
then
    PYTEST_DEBUG_ARGS=(-s -v)
else
    PYTEST_DEBUG_ARGS=()
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
    packages/test_api/src/galaxy_test/api/test_datatypes.py
    packages/test_api/src/galaxy_test/api/test_workflow_extraction.py
    packages/test_api/src/galaxy_test/api/test_users.py
    packages/test_api/src/galaxy_test/api/test_roles.py
    packages/test_api/src/galaxy_test/api/test_authenticate.py
    packages/test_api/src/galaxy_test/api/test_configuration.py
    packages/test_api/src/galaxy_test/api/test_dataset_collections.py
    packages/test_api/src/galaxy_test/api/test_display_applications.py
    packages/test_api/src/galaxy_test/api/test_drs.py
    packages/test_api/src/galaxy_test/api/test_folders.py
    packages/test_api/src/galaxy_test/api/test_folder_contents.py
    packages/test_api/src/galaxy_test/api/test_framework.py
    packages/test_api/src/galaxy_test/api/test_histories.py
    packages/test_api/src/galaxy_test/api/test_history_contents.py
)
selenium_tests=(
    packages/test_selenium/src/galaxy_test/selenium/test_anon_history.py
    packages/test_selenium/src/galaxy_test/selenium/test_collection_builders.py
    packages/test_selenium/src/galaxy_test/selenium/test_dataset_metadata_download.py
    packages/test_selenium/src/galaxy_test/selenium/test_collection_edit.py
    packages/test_selenium/src/galaxy_test/selenium/test_history_copy_elements.py
    packages/test_selenium/src/galaxy_test/selenium/test_history_dataset_state.py
    packages/test_selenium/src/galaxy_test/selenium/test_history_multi_view.py
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

echo "Running tests: ${tests[*]}"
# pytest markers to select against. In order to not cause an explosion of
# semi-permanent artifacts that are difficult to manage tests which require
# new libraries or users are disabled. Tests which require admin keys are
# also disabled for security/simplicity reasons. Publishing objects is disabled
# to avoid exposing deployment test artifacts. Runtime checks catch helpers used
# by tests without requirement markers.
export GALAXY_TEST_SKIP_IF_REQUIRES_ADMIN=1
export GALAXY_TEST_SKIP_IF_REQUIRES_NEW_USER=1
export GALAXY_TEST_SKIP_IF_REQUIRES_NEW_LIBRARY=1
export GALAXY_TEST_SKIP_IF_REQUIRES_NEW_PUBLISHED_OBJECTS=1
export GALAXY_TEST_SKIP_IF_REQUIRES_CELERY=1
PYTEST_MARKER_EXPRESSION="not requires_admin and not requires_new_library and not requires_new_user and not requires_celery and not requires_new_published_objects"
PYTEST_HTML_REPORT="deployment_tests.html"
pytest \
    "${PYTEST_DEBUG_ARGS[@]}" \
    --html "$PYTEST_HTML_REPORT" \
    -m "${PYTEST_MARKER_EXPRESSION}" \
    "${tests[@]}"
