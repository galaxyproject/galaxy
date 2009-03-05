#!/bin/sh

cd `dirname $0`
python -ES ./scripts/paster.py serve universe_wsgi.ini $@
