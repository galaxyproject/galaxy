#!/bin/bash
#
# Install packages in development mode, for running installed Galaxy from the source
#
set -euo pipefail

up_to="${1:-}"

if [ -n "$up_to" -a ! -d "$up_to" ]; then
    echo "ERROR: package does not exist: $up_to"
    exit 1
fi

while read package; do
    [ -n "$package" ] || continue
    pushd $package
    pip install -e .
    popd
    [ "$package" != "$up_to" ] || exit
done < packages_by_dep_dag.txt
