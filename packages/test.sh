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
pip install --upgrade pip setuptools wheel
pip install -r../lib/galaxy/dependencies/pinned-typecheck-requirements.txt

# ensure ordered by dependency DAG
while read -r package_dir; do
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

    # Prevent execution of alembic/env.py at test collection stage (alembic.context not set)
    # Also ignore functional tests (galaxy_test/ and tool_shed/test/).
    unit_extra='--doctest-modules --ignore=galaxy/model/migrations/alembic/ --ignore=galaxy_test/
		--ignore=tool_shed/test/ --ignore=tool_shed/webapp/model/migrations/alembic/'
    # Ignore exit code 5 (no tests ran)
    pytest $unit_extra -m 'not external_dependency_management' . || test $? -eq 5
    make mypy
    cd ..
done < packages_by_dep_dag.txt
