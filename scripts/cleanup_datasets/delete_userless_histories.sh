#!/bin/sh

# This script must be executed from the $UNIVERSE_HOME directory
# e.g., sh ./scripts/cleanup_datasets/purge_delete_userless_histories.sh

. ./scripts/get_python.sh
. ./setup_paths.sh

$GALAXY_PYTHON ./scripts/cleanup_datasets/cleanup_datasets.py ./universe_wsgi.ini -d 10 -2 $@ >> ./scripts/cleanup_datasets/delete_userless_histories.log
