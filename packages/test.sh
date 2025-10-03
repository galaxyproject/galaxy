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
    for pkg in ${SKIP_PACKAGES[@]}; do
        [[ $1 == $pkg ]] && return 0
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

# Use a throw-away virtualenv
TEST_PYTHON=${TEST_PYTHON:-"python3"}
TEST_ENV_DIR=${TEST_ENV_DIR:-$(mktemp -d -t gxpkgtestenvXXXXXX)}

# Install uv for fast package installation
if ! command -v uv >/dev/null; then
    echo "Installing uv..."
    if command -v curl >/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh || "$TEST_PYTHON" -m pip install uv
    elif command -v wget >/dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh || "$TEST_PYTHON" -m pip install uv
    else
        "$TEST_PYTHON" -m pip install uv
    fi
    export PATH="$HOME/.local/bin:$PATH"
fi

# Use uv venv for much faster virtual environment creation
uv venv "$TEST_ENV_DIR" --python "$TEST_PYTHON"
# shellcheck disable=SC1091
. "${TEST_ENV_DIR}/bin/activate"

# Note: No need to upgrade pip anymore since we're using uv exclusively
if [ $FOR_PULSAR -eq 0 ]; then
    uv pip install -r../lib/galaxy/dependencies/pinned-typecheck-requirements.txt
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

    # Install extras (if needed)
    if [ "$package_dir" = "util" ]; then
        uv pip install '.[image-util,template,jstree,config-template,test]'
    elif [ "$package_dir" = "tool_util" ]; then
        uv pip install '.[cwl,mulled,edam,extended-assertions,test]'
    elif grep -q 'test =' setup.cfg 2>/dev/null; then
        uv pip install '.[test]'
    else
        uv pip install .
    fi

    if [ $FOR_PULSAR -eq 0 ]; then
        marker_args=(-m 'not external_dependency_management')
    else
        marker_args=()
    fi
    # Ignore exit code 5 (no tests ran)
    pytest "${marker_args[@]}" . || test $? -eq 5
    if [ $FOR_PULSAR -eq 0 ]; then
        # make mypy uses uv now and so this legacy code should just run mypy
        # directly to use the venv we have already activated
        mypy .
    fi
    cd ..
done < $PACKAGE_LIST_FILE
