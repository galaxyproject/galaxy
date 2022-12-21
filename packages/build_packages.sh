#!/bin/bash

# Builds packages, sets new versions, but doesn't upload anything to pypi.
# Set DEV_RELEASE=1 to build the dev of packages.

set -ex

# Change to packages directory.
cd "$(dirname "$0")"

# ensure ordered by dependency dag
while read -r package_dir; do
    printf "\n========= RELEASING PACKAGE ${package_dir} =========\n\n"

    cd "$package_dir"

    make clean
    make commit-version
    make dist
    make new-version

    cd ..
done < packages_by_dep_dag.txt
