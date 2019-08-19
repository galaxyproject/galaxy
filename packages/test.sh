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

# Packages must be ordered by dependency DAG
PACKAGE_DIRS=(
    util
    objectstore
    job_metrics
    containers
    data
    test_tools
    model_tools
    tool_util
    job_execution
    auth
    authnz
    web_stack
    web_framework
    app
    web_apps
)
# Whether packages are ready to be tested
RUN_TESTS=(1 1 1 1 1 1 1 1 1 0 0 0 0)
for ((i=0; i<${#PACKAGE_DIRS[@]}; i++)); do
    package_dir=${PACKAGE_DIRS[$i]}
    run_tests=${RUN_TESTS[$i]}

    cd "$package_dir"
    make dist
    pip install dist/*.whl
    if [ "$package_dir" = "util" ]; then
        pip install "$(echo dist/*.whl)[template,jstree]"
    fi

    if [[ "$run_tests" == "1" ]]; then
        pytest --doctest-modules galaxy tests
    fi
    cd ..
done
