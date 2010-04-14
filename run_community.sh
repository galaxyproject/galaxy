#!/bin/sh

cd `dirname $0`
python ./scripts/paster.py serve community_wsgi.ini --pid-file=community_webapp.pid --log-file=community_webapp.log $@
