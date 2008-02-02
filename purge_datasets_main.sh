#!/bin/sh

source ./setup_paths.sh

python2.4 ./scripts/cleanup_datasets.py ./universe_wsgi.ini -6 $@ >> ./purge_datasets.log
