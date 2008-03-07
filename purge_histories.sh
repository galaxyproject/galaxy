#!/bin/sh

source ./setup_paths.sh

python2.4 ./scripts/cleanup_datasets.py ./universe_wsgi.ini -d 10 -4 -r $@ >> ./purge_histories.log
