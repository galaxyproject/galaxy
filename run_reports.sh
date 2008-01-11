#!/bin/sh

source setup_paths.sh

python2.4 ./scripts/paster.py serve reports_wsgi.ini $@
