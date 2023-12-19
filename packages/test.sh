#!/bin/bash

set -ex

PACKAGE_LIST_FILE=packages_by_dep_dag.txt
FOR_PULSAR=0

for arg in "$@"; do
    if [ "$arg" = "--for-pulsar" ]; then
        PACKAGE_LIST_FILE=packages_for_pulsar_by_dep_dag.txt
        FOR_PULSAR=1
    fi
done

# Don't display the pip progress bar when running under CI
if [ "$CI" = 'true' ]; then
    export PIP_PROGRESS_BAR=off
fi

# Change to packages directory.
cd "$(dirname "$0")"

# Use a throw-away virtualenv
TEST_PYTHON=${TEST_PYTHON:-"python"}
TEST_ENV_DIR=${TEST_ENV_DIR:-$(mktemp -d -t gxpkgtestenvXXXXXX)}

virtualenv -p "$TEST_PYTHON" "$TEST_ENV_DIR"
. "${TEST_ENV_DIR}/bin/activate"
pip install --upgrade pip setuptools wheel
if [ $FOR_PULSAR -eq 0 ]; then
    pip install -r../lib/galaxy/dependencies/pinned-typecheck-requirements.txt
fi

# ensure ordered by dependency DAG
while read -r package_dir || [ -n "$package_dir" ]; do  # https://stackoverflow.com/questions/12916352/shell-script-read-missing-last-line
    if [ -z "$package_dir" ]; then
        # Skip empty lines
        continue
    fi
    printf "\n========= TESTING PACKAGE ${package_dir} =========\n\n"

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

    if [ $FOR_PULSAR -eq 0 ]; then
        marker_args=(-m 'not external_dependency_management')
    else
        marker_args=()
    fi
    # Prevent execution of alembic/env.py at test collection stage (alembic.context not set)
    # Also ignore functional tests (galaxy_test/ and tool_shed/test/).
    unit_extra=(--doctest-modules --ignore=galaxy/model/migrations/alembic/ --ignore=galaxy_test/ --ignore=tool_shed/test/ --ignore=tool_shed/webapp/model/migrations/alembic/ "${marker_args[@]}")
    # Ignore exit code 5 (no tests ran)
    pytest "${unit_extra[@]}" . || test $? -eq 5
    if [ $FOR_PULSAR -eq 0 ]; then
        make mypy
    fi
    cd ..
done < $PACKAGE_LIST_FILE
