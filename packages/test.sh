#!/bin/bash

set -ex

PACKAGE_LIST_FILE=packages_by_dep_dag.txt
FOR_PULSAR=0
SKIP_PACKAGES=(
    web_client
    meta
)

should_skip_package() {
    local pkg
    for pkg in "${SKIP_PACKAGES[@]}"; do
        [ "$1" = "$pkg" ] && return 0
    done
    return 1
}

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

TEST_PYTHON=${TEST_PYTHON:-"python3"}

if command -v uv >/dev/null; then
    VENV_CMD="uv venv --python $TEST_PYTHON"
    PIP_CMD="$(command -v uv) pip"
    BUILD_WHEEL_CMD="$(command -v uv) build"
    TWINE_CMD="$(command -v uvx) twine"
    export UV_EXTRA_INDEX_URL=https://wheels.galaxyproject.org/simple
    export UV_INDEX_STRATEGY=unsafe-best-match
else
    VENV_CMD="$TEST_PYTHON -m venv"
    PIP_CMD='python -m pip'
    BUILD_WHEEL_CMD='python -m build'
    TWINE_CMD=twine
    export PIP_EXTRA_INDEX_URL=https://wheels.galaxyproject.org/simple
fi

# Ensure ordered by dependency DAG
while read -r package_dir || [ -n "$package_dir" ]; do  # https://stackoverflow.com/questions/12916352/shell-script-read-missing-last-line
    # Ignore empty lines
    if [ -z "$package_dir" ]; then
        continue
    fi
    # Ignore lines beginning with `#`
    if  [[ $package_dir =~ ^#.* ]]; then
        continue
    fi
    if should_skip_package "$package_dir"; then
        printf "\nSkipping package %s\n\n" "$package_dir"
        continue
    fi

    printf "\n========= TESTING PACKAGE %s =========\n\n" "$package_dir"

    cd "$package_dir"

    # Use a throw-away virtualenv
    TEST_ENV_DIR=$(mktemp -d -t gxpkgtestenvXXXXXX)
    ${VENV_CMD} "${TEST_ENV_DIR}"
    # shellcheck disable=SC1091
    . "${TEST_ENV_DIR}/bin/activate"
    if [ "${PIP_CMD}" = 'python -m pip' ]; then
        ${PIP_CMD} install --upgrade build pip setuptools twine wheel
    fi

    # Install extras (if needed)
    if [ "$package_dir" = "util" ]; then
        ${PIP_CMD} install '.[image-util,template,jstree,config-template,test]'
    elif [ "$package_dir" = "tool_util" ]; then
        ${PIP_CMD} install '.[cwl,mulled,edam,extended-assertions,test]'
    elif grep -q '^test = \[' pyproject.toml 2>/dev/null; then
        ${PIP_CMD} install '.[test]'
    else
        ${PIP_CMD} install .
    fi

    if [ $FOR_PULSAR -eq 0 ]; then
        marker_args=(-m 'not external_dependency_management')
    else
        marker_args=()
    fi
    # Ignore exit code 5 (no tests ran)
    pytest "${marker_args[@]}" . || test $? -eq 5
    if [ $FOR_PULSAR -eq 0 ]; then
        ${PIP_CMD} install -r ../../lib/galaxy/dependencies/pinned-typecheck-requirements.txt
        # make mypy uses uv now and so this legacy code should just run mypy
        # directly to use the venv we have already activated
        cd src
        mypy .
        cd ..
        if [ -d tests ]; then
            mypy tests
        fi

        ${BUILD_WHEEL_CMD} -o dist
        ${TWINE_CMD} check dist/*
    fi
    cd ..
    deactivate
    rm -rf "${TEST_ENV_DIR}"
done < $PACKAGE_LIST_FILE
