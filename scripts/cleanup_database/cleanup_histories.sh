#!/bin/sh

#######
# TODO add description
#######

cd "$(dirname "$0")"/../.. || exit
python ./scripts/cleanup_database/cleanup_histories.py "$@"
