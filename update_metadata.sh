#!/bin/sh

source setup_paths.sh

python2.4 ./scripts/update_metadata.py universe_wsgi.ini $@
