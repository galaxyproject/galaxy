#!/bin/sh

. ./scripts/get_python.sh
. ./setup_paths.sh

$GALAXY_PYTHON ./scripts/paster.py serve reports_wsgi.ini --pid-file=reports_webapp.pid --log-file=reports_webapp.log $@
