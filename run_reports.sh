#!/bin/sh

cd `dirname $0`

python -ES ./scripts/paster.py serve reports_wsgi.ini --pid-file=reports_webapp.pid --log-file=reports_webapp.log $@
