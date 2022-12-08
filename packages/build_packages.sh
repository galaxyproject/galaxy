#!/bin/bash

# Builds packages, sets new versions, but doesn't upload anything to pypi.
# Set DEV_RELEASE=1 to build the dev of packages.

set -ex

# Change to packages directory.
cd "$(dirname "$0")"

# ensure ordered by dependency dag
PACKAGE_DIRS=(
    util
    objectstore
    job_metrics
    config
    files
    tool_util
    data
    job_execution
    auth
    web_stack
    web_framework
    app
    webapps
    test_base
    test_driver
    test_api
)
for ((i=0; i<${#PACKAGE_DIRS[@]}; i++)); do
    printf "\n========= RELEASING PACKAGE ${PACKAGE_DIRS[$i]} =========\n\n"
    package_dir=${PACKAGE_DIRS[$i]}

    cd "$package_dir"

    make clean
    make commit-version
    make dist
    make new-version

    cd ..
done
