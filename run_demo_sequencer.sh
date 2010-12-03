#!/bin/sh

cd `dirname $0`
python ./scripts/paster.py serve demo_sequencer_wsgi.ini --pid-file=demo_sequencer_webapp.pid --log-file=demo_sequencer_webapp.log $@