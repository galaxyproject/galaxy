#!/bin/sh

source ./setup_paths.sh

python2.4 ./scripts/cleanup_datasets.py ./universe_wsgi.ini -d 60 -2 $@ >> ./delete_userless_histories.log
