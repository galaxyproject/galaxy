#!/bin/bash

set -ex

# Don't display the pip progress bar when running under CI
[ "$CI" = 'true' ] && export PIP_PROGRESS_BAR=off

# Change to packages directory.
cd "$(dirname "$0")"

# Use a throw-away virtualenv
TEST_PYTHON=${TEST_PYTHON:-"python"}
TEST_ENV_DIR=${TEST_ENV_DIR:-$(mktemp -d -t gxpkgtestenvXXXXXX)}

virtualenv -p "$TEST_PYTHON" "$TEST_ENV_DIR"
. "${TEST_ENV_DIR}/bin/activate"
pip install --upgrade pip 'setuptools<58' wheel
pip install -r../lib/galaxy/dependencies/pinned-lint-requirements.txt

# ensure ordered by dependency dag
PACKAGE_DIRS=(
    util
    objectstore
    job_metrics
    containers
    files
    tool_util
    data
    job_execution
    auth
    web_stack
    web_framework
    app
    webapps
)
RUN_TESTS=(1 1 1 1 1 1 1 1 1 1 1 1 1)
RUN_MYPY=(1 1 1 1 1 1 1 1 1 1 1 1 1)
for ((i=0; i<${#PACKAGE_DIRS[@]}; i++)); do
    printf "\n========= TESTING PACKAGE ${PACKAGE_DIRS[$i]} =========\n\n"
    package_dir=${PACKAGE_DIRS[$i]}

    cd "$package_dir"

    # Install extras (if needed)
    if [ "$package_dir" = "util" ]; then
        pip install -e '.[template,jstree]'
    elif [ "$package_dir" = "tool_util" ]; then
        pip install -e '.[cwl,mulled,edam]'
    else
        pip install -e '.'
    fi

    pip install -r test-requirements.txt

    if [[ "${RUN_TESTS[$i]}" == "1" ]]; then
        pytest --doctest-modules galaxy tests
    fi
    if [[ "${RUN_MYPY[$i]}" == "1" ]]; then
        make mypy
    fi
    cd ..
done
