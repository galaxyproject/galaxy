#!/bin/bash

# Builds packages, sets new versions, but doesn't upload anything to pypi.
# Set DEV_RELEASE=1 to build the dev of packages.

set -ex

# Change to packages directory.
cd "$(dirname "$0")"

# ensure ordered by dependency dag
while read -r package_dir; do
    if [ -z "$package_dir" ]; then
        # Skip empty lines
        continue
    fi
    printf "\n========= RELEASING PACKAGE %s =========\n\n" "$package_dir"
    
    cd "$package_dir"
    
    make clean
    make commit-version
    make dist
    make new-version
    
    cd ..
done < packages_by_dep_dag.txt
