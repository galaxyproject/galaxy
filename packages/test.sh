#!/bin/bash

set -e

# Don't display the pip progress bar when running under CI
[ "$CI" = 'true' ] && export PIP_PROGRESS_BAR=off

# Change to packages directory.
cd "$(dirname "$0")"

# Use a throw-away virtualenv
TEST_PYTHON=${TEST_PYTHON:-"python"}
TEST_ENV_DIR=${TEST_ENV_DIR:-$(mktemp -d -t gxpkgtestenvXXXXXX)}

virtualenv -p "$TEST_PYTHON" "$TEST_ENV_DIR"
. "${TEST_ENV_DIR}/bin/activate"
pip install pytest

# ensure ordered by dependency dag
PACKAGE_DIRS=(
    util
    objectstore
    job_metrics
    containers
    tool_util
    data
    job_execution
    auth
    web_stack
    web_framework
    app
    web_apps
)
# tool_util not yet working 100%,
# data has many problems quota, tool shed install database, etc..
RUN_TESTS=(1 1 1 1 1 1 1 1 0 0 0 0)
for ((i=0; i<${#PACKAGE_DIRS[@]}; i++)); do
    package_dir=${PACKAGE_DIRS[$i]}
    run_tests=${RUN_TESTS[$i]}

    cd "$package_dir"
    pip install -e .
    # Install extras (if needed)
    if [ "$package_dir" = "util" ]; then
        pip install -e '.[template,jstree]'
    fi
    if [ "$package_dir" = "tool_util"]; then
        pip install -e '.[condatesting]'
    fi

    if [[ "$run_tests" == "1" ]]; then
        pytest --doctest-modules galaxy tests
    fi
    cd ..
done
