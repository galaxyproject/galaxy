#!/bin/sh

. ./scripts/get_python.sh
. ./setup_paths.sh

$GALAXY_PYTHON ./scripts/cleanup_datasets.py ./universe_wsgi.ini -d 10 -2 $@ >> ./delete_userless_histories.log
