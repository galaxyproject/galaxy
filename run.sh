#!/bin/sh

cd `dirname $0`
python2.52.5 -ES ./scripts/paster.py serve universe_wsgi.ini $@
