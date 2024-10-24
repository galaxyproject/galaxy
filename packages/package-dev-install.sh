#!/bin/bash
#
# Install packages in development mode, for running installed Galaxy from the source
#
set -euo pipefail

editable=false

while getopts ':e' OPTION
do
    case $OPTION in
        e)
            editable=true
           ;;
    esac
done
shift $((OPTIND - 1))

up_to="${1:-}"

if [ -n "$up_to" -a ! -d "$up_to" ]; then
    echo "ERROR: package does not exist: $up_to"
    exit 1
fi

while read package; do
    [ -n "$package" ] || continue
    pushd $package
    if $editable; then
        pip install -e .
    else
        pip install .
    fi
    popd
    [ "$package" != "$up_to" ] || exit
done < packages_by_dep_dag.txt
